"""clear relative image_url values from watches and products

Revision ID: 0023
Revises: 0022
Create Date: 2026-05-31 00:00:00.000000

Relative image paths (e.g. /Images/915x900/xxx.jpg) were stored without
the shop domain prefix. Clearing them so the next scrape saves absolute URLs.
"""
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clear any image_url that is not an absolute http(s) URL.
    # The next scrape will re-save them with the correct absolute URL.
    op.execute(
        "UPDATE watches SET image_url = NULL "
        "WHERE image_url IS NOT NULL "
        "AND image_url NOT LIKE 'http://%' "
        "AND image_url NOT LIKE 'https://%'"
    )
    op.execute(
        "UPDATE products SET image_url = NULL "
        "WHERE image_url IS NOT NULL "
        "AND image_url NOT LIKE 'http://%' "
        "AND image_url NOT LIKE 'https://%' "
        "AND image_url NOT LIKE '/api/v1/uploads/%' "
        "AND image_url NOT LIKE '/api/uploads/%'"
    )


def downgrade() -> None:
    # Intentionally a no-op — we cannot recover the relative paths.
    pass
