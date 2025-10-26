from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_payment_search_vector_payment_idx_payment_search'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- 트리거 함수 생성
            CREATE OR REPLACE FUNCTION update_payment_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('simple', COALESCE(NEW.payment_type, '')), 'B') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.status, '')), 'B');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            -- 트리거 생성
            CREATE TRIGGER payment_search_vector_update
            BEFORE INSERT OR UPDATE ON payments
            FOR EACH ROW
            EXECUTE FUNCTION update_payment_search_vector();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS payment_search_vector_update ON payments;
            DROP FUNCTION IF EXISTS update_payment_search_vector();
            """,
        ),
    ]
