"""Вход по почте и паролю, несколько OAuth-провайдеров, синхронизация с несколькими календарями

- users: + email_verified, password_hash, avatar_url; email уникален; − yandex_id, login, avatar_id
- yandex_tokens + calendar_links → oauth_accounts (provider = yandex)
- events.sync_status/sync_error → event_syncs (по строке на событие и аккаунт)

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("access_token_enc", sa.Text(), nullable=False),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("calendar_access", sa.Boolean(), nullable=False),
        sa.Column("sync_enabled", sa.Boolean(), nullable=False),
        sa.Column("calendar_id", sa.Text(), nullable=True),
        sa.Column("calendar_status", sa.String(length=16), nullable=False),
        sa.Column("calendar_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_oauth_accounts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_accounts")),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_accounts_provider_user"),
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_accounts_user_provider"),
    )
    op.create_index(op.f("ix_oauth_accounts_user_id"), "oauth_accounts", ["user_id"], unique=False)

    op.create_table(
        "event_syncs",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("remote_id", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["oauth_accounts.id"], name=op.f("fk_event_syncs_account_id_oauth_accounts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name=op.f("fk_event_syncs_event_id_events"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "account_id", name=op.f("pk_event_syncs")),
    )

    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))

    # --- Перенос данных -----------------------------------------------------------------------
    # Все прежние пользователи пришли через Яндекс: почта подтверждена, токены и календарь — в oauth_accounts.
    # Старые токены выдавались со всеми правами приложения (scope = NULL), т.е. с calendar:all.
    op.execute(
        """
        INSERT INTO oauth_accounts (
            id, user_id, provider, provider_user_id, email, access_token_enc, refresh_token_enc, expires_at, scope,
            calendar_access, sync_enabled, calendar_id, calendar_status, calendar_error, created_at, updated_at
        )
        SELECT
            gen_random_uuid(), u.id, 'yandex', u.yandex_id, lower(u.email),
            coalesce(t.access_token_enc, ''), t.refresh_token_enc, t.expires_at,
            coalesce(t.scope, 'login:info login:email calendar:all'),
            t.user_id IS NOT NULL AND (t.scope IS NULL OR t.scope LIKE '%calendar:all%'),
            t.user_id IS NOT NULL AND (t.scope IS NULL OR t.scope LIKE '%calendar:all%'),
            cl.calendar_url, coalesce(cl.status, 'pending'), cl.error,
            u.created_at, now()
        FROM users u
        LEFT JOIN yandex_tokens t ON t.user_id = u.id
        LEFT JOIN calendar_links cl ON cl.user_id = u.id
        """
    )
    op.execute(
        """
        UPDATE users SET
            email = lower(email),
            email_verified = email IS NOT NULL,
            avatar_url = CASE WHEN avatar_id IS NOT NULL
                THEN 'https://avatars.yandex.net/get-yapic/' || avatar_id || '/islands-200' END
        """
    )
    # Уже выгруженные события и ошибки выгрузки; pending/disabled выгрузятся заново при следующей синхронизации
    op.execute(
        """
        INSERT INTO event_syncs (event_id, account_id, remote_id, status, error, updated_at)
        SELECT e.id, a.id, e.ical_uid, e.sync_status, e.sync_error, now()
        FROM events e
        JOIN oauth_accounts a ON a.user_id = e.user_id AND a.provider = 'yandex'
        WHERE e.sync_status IN ('synced', 'error')
        """
    )

    # --- Удаление старого ---------------------------------------------------------------------
    op.drop_column("events", "sync_status")
    op.drop_column("events", "sync_error")
    op.drop_constraint("uq_users_yandex_id", "users", type_="unique")
    op.drop_column("users", "yandex_id")
    op.drop_column("users", "login")
    op.drop_column("users", "avatar_id")
    op.create_unique_constraint(op.f("uq_users_email"), "users", ["email"])
    op.alter_column("users", "email_verified", server_default=None)
    op.drop_table("calendar_links")
    op.drop_table("yandex_tokens")


def downgrade() -> None:
    raise NotImplementedError(
        "Откат 0002 не поддерживается: пользователи с паролем и Google не помещаются в старую схему. "
        "Восстановите базу из резервной копии."
    )
