"""Tests for services/measurements.py: CRUD and per-user ownership isolation."""

from datetime import datetime

import pytest

from models.measurement import MeasurementIn, MeasurementUpdate
from services import measurements


def _measurement_data(**overrides):
    data = dict(
        height_cm=180.0,
        weight_kg=75.0,
        chest_cm=100.0,
        waist_cm=85.0,
        hip_cm=95.0,
        thigh_cm=55.0,
        calf_cm=38.0,
        arm_cm=32.0,
        forearm_cm=27.0,
        recorded_at=datetime(2026, 1, 1, 8, 0, 0),
    )
    data.update(overrides)
    return data


def test_create_measurement(db_session, test_user):
    measurement = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), test_user.id
    )
    assert measurement.id is not None
    assert measurement.user_id == test_user.id
    assert measurement.height_cm == 180.0


def test_list_all_scoped_to_user(db_session, test_user, other_user):
    measurements.create(
        db_session, MeasurementIn(**_measurement_data(weight_kg=70.0)), test_user.id
    )
    measurements.create(
        db_session, MeasurementIn(**_measurement_data(weight_kg=90.0)), other_user.id
    )

    mine = measurements.list_all(db_session, test_user.id)
    assert [m.weight_kg for m in mine] == [70.0]


def test_get_measurement_success(db_session, test_user):
    created = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), test_user.id
    )
    fetched = measurements.get(db_session, created.id, test_user.id)
    assert fetched.id == created.id


def test_get_measurement_not_found_raises(db_session, test_user):
    with pytest.raises(measurements.MeasurementNotFoundError):
        measurements.get(db_session, 999, test_user.id)


def test_get_measurement_owned_by_other_user_raises_not_found(db_session, test_user, other_user):
    created = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), other_user.id
    )
    with pytest.raises(measurements.MeasurementNotFoundError):
        measurements.get(db_session, created.id, test_user.id)


def test_update_measurement(db_session, test_user):
    created = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), test_user.id
    )
    updated = measurements.update(
        db_session,
        created.id,
        MeasurementUpdate(**_measurement_data(weight_kg=72.5)),
        test_user.id,
    )
    assert updated.weight_kg == 72.5


def test_update_measurement_not_found_raises(db_session, test_user):
    with pytest.raises(measurements.MeasurementNotFoundError):
        measurements.update(
            db_session, 999, MeasurementUpdate(**_measurement_data()), test_user.id
        )


def test_update_measurement_owned_by_other_user_raises_not_found(
    db_session, test_user, other_user
):
    created = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), other_user.id
    )
    with pytest.raises(measurements.MeasurementNotFoundError):
        measurements.update(
            db_session, created.id, MeasurementUpdate(**_measurement_data()), test_user.id
        )


def test_delete_measurement(db_session, test_user):
    created = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), test_user.id
    )
    measurements.delete(db_session, created.id, test_user.id)
    with pytest.raises(measurements.MeasurementNotFoundError):
        measurements.get(db_session, created.id, test_user.id)


def test_delete_measurement_owned_by_other_user_raises_not_found(
    db_session, test_user, other_user
):
    created = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), other_user.id
    )
    with pytest.raises(measurements.MeasurementNotFoundError):
        measurements.delete(db_session, created.id, test_user.id)


def test_calculate_bmi_correctness():
    # 75 kg over 1.8 m: 75 / 3.24 = 23.148148... -> rounds to 23.1
    assert measurements.calculate_bmi(180.0, 75.0) == 23.1


def test_calculate_bmi_halfway_rounds_to_even_down():
    # height_m=2.0m so height_m**2=4.0 exactly; 89.0 / 4.0 = 22.25 exactly
    # (both are exact binary fractions, so this is a true halfway tie, not
    # floating-point noise). 22.25 sits exactly between 22.2 and 22.3; Python's
    # round-half-to-even picks 22.2, since 2 is the even digit.
    result = measurements.calculate_bmi(200.0, 89.0)
    assert result == 22.2


def test_calculate_bmi_halfway_rounds_to_even_up():
    # Same setup, but 91.0 / 4.0 = 22.75 exactly: a true halfway tie between
    # 22.7 and 22.8. Round-half-to-even picks 22.8, since 8 is the even digit
    # (the opposite direction from the down case above, confirming the
    # rounding follows the even digit rather than always rounding down/up).
    result = measurements.calculate_bmi(200.0, 91.0)
    assert result == 22.8


def test_measurement_out_bmi_field_matches_calculate_bmi(db_session, test_user):
    created = measurements.create(
        db_session, MeasurementIn(**_measurement_data()), test_user.id
    )
    assert created.bmi == measurements.calculate_bmi(created.height_cm, created.weight_kg)
