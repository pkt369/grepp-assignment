from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_course_search_vector_course_idx_course_search'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- 트리거 함수 생성
            CREATE OR REPLACE FUNCTION update_course_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('simple', COALESCE(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.description, '')), 'B');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            -- 트리거 생성
            CREATE TRIGGER course_search_vector_update
            BEFORE INSERT OR UPDATE ON courses
            FOR EACH ROW
            EXECUTE FUNCTION update_course_search_vector();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS course_search_vector_update ON courses;
            DROP FUNCTION IF EXISTS update_course_search_vector();
            """,
        ),
    ]
