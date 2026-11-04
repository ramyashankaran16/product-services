
from alembic import op
import sqlalchemy as sa




def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("price > 0", name="ck_products_price_positive"),
        sa.CheckConstraint("quantity >= 0", name="ck_products_quantity_non_negative"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_products_status"),
    )
    op.create_index("uq_products_name_lower", "products", [sa.text("lower(name)")], unique=True)
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_status", "products", ["status"])


def downgrade() -> None:
    op.drop_index("ix_products_status", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("uq_products_name_lower", table_name="products")
    op.drop_table("products")
