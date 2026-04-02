import os
from typing import Any, cast

import pytest
from app.core.database import Base
from app.services.user_service import UserService
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

pytestmark = [pytest.mark.regression, pytest.mark.postgres_regression]


POSTGRES_TEST_URL = os.getenv("TEST_POSTGRES_DATABASE_URL") or os.getenv("DATABASE_URL", "")


requires_postgres = pytest.mark.skipif(
    not (os.getenv("RUN_POSTGRES_REGRESSION") == "1" and POSTGRES_TEST_URL.startswith("postgresql")),
    reason="Set RUN_POSTGRES_REGRESSION=1 and TEST_POSTGRES_DATABASE_URL to run Postgres regression tests",
)


@requires_postgres
def test_register_recovers_from_sequence_drift_on_postgres():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        db.commit()

        seed = UserService.create_user(
            db,
            username="seed_user",
            email="seed_user@example.com",
            password="StrongPass_2026!",
        )
        seed_id = cast(int, cast(Any, seed).id)
        assert seed_id == 1

        # Force sequence drift so next INSERT tries id=1 again.
        db.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence('users', 'id'),
                    1,
                    false
                )
                """
            )
        )
        db.commit()

        recovered = UserService.create_user(
            db,
            username="recovered_user",
            email="recovered_user@example.com",
            password="StrongPass_2026!",
        )

        recovered_id = cast(int, cast(Any, recovered).id)
        assert recovered_id > 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_register_unique_conflict_still_returns_400_on_postgres():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        db.commit()

        UserService.create_user(
            db,
            username="dup_user",
            email="dup_user@example.com",
            password="StrongPass_2026!",
        )

        with pytest.raises(HTTPException) as exc:
            UserService.create_user(
                db,
                username="dup_user_2",
                email="dup_user@example.com",
                password="StrongPass_2026!",
            )

        assert exc.value.status_code == 400
        assert exc.value.detail == "Username or email already exists"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
