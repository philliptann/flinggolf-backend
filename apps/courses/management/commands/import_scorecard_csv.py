# backend/apps/courses/management/commands/import_scorecard_csv.py

# Run it like this:
#sudo docker compose -f docker-compose.prod.yml exec backend python manage.py import_scorecard_csv /app/flinggolf_course_import_example_beamish.csv
#To allow updates to existing rows:
# sudo docker compose -f docker-compose.prod.yml exec backend python manage.py import_scorecard_csv /app/flinggolf_course_import_example_beamish.csv --update

#After importing, verify with:
# sudo docker compose -f docker-compose.prod.yml exec backend python manage.py shell -c "from apps.courses.models import Club, Course, Hole, TeeSet, TeeSetHole; print('Clubs', Club.objects.count()); print('Courses', Course.objects.count()); print('Holes', Hole.objects.count()); print('TeeSets', TeeSet.objects.count()); print('TeeSetHoles', TeeSetHole.objects.count())"

import csv
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.courses.models import Club, Course, Hole, TeeSet, TeeSetHole


class Command(BaseCommand):
    help = "Import course, tee set, hole, and tee-set-hole data from a CSV file."

    REQUIRED_COLUMNS = {
        "club_name",
        "club_city",
        "club_region",
        "club_country",
        "club_postcode",
        "course_name",
        "course_holes",
        "course_par_total",
        "tee_name",
        "tee_colour",
        "gender_category",
        "tee_par_total",
        "course_rating",
        "slope_rating",
        "sss_value",
        "hole_number",
        "hole_default_par",
        "hole_default_stroke_index",
        "tee_yardage",
        "tee_par",
        "tee_stroke_index",
    }

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the CSV file")
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing rows if found",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        allow_update = options["update"]

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        rows = self._read_csv(csv_path)
        if not rows:
            raise CommandError("CSV file is empty.")

        self._validate_columns(rows[0].keys())
        self._validate_row_data(rows)

        with transaction.atomic():
            summary = self._import_rows(rows, allow_update=allow_update)

        self.stdout.write(self.style.SUCCESS("Import complete."))
        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")

    def _read_csv(self, csv_path: Path):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _validate_columns(self, columns):
        missing = self.REQUIRED_COLUMNS - set(columns)
        if missing:
            raise CommandError(f"Missing required columns: {', '.join(sorted(missing))}")

    def _validate_row_data(self, rows):
        for idx, row in enumerate(rows, start=2):
            try:
                self._to_int(row["course_holes"], "course_holes", idx)
                self._to_int(row["course_par_total"], "course_par_total", idx)
                self._to_int(row["tee_par_total"], "tee_par_total", idx)
                self._to_int(row["slope_rating"], "slope_rating", idx)
                self._to_int(row["hole_number"], "hole_number", idx)
                self._to_int(row["hole_default_par"], "hole_default_par", idx)
                self._to_int(row["hole_default_stroke_index"], "hole_default_stroke_index", idx)
                self._to_int(row["tee_yardage"], "tee_yardage", idx)
                self._to_int(row["tee_par"], "tee_par", idx)
                self._to_int(row["tee_stroke_index"], "tee_stroke_index", idx)
                self._to_decimal_str(row["course_rating"], "course_rating", idx)

                if row["sss_value"].strip():
                    self._to_decimal_str(row["sss_value"], "sss_value", idx)

                if not row["club_name"].strip():
                    raise CommandError(f"Row {idx}: club_name is required")
                if not row["course_name"].strip():
                    raise CommandError(f"Row {idx}: course_name is required")
                if not row["tee_name"].strip():
                    raise CommandError(f"Row {idx}: tee_name is required")
                if not row["tee_colour"].strip():
                    raise CommandError(f"Row {idx}: tee_colour is required")
                if not row["gender_category"].strip():
                    raise CommandError(f"Row {idx}: gender_category is required")

            except ValueError as e:
                raise CommandError(str(e)) from e

        # Duplicate check within CSV for tee+hole
        seen = set()
        for idx, row in enumerate(rows, start=2):
            key = (
                row["club_name"].strip().lower(),
                row["course_name"].strip().lower(),
                row["tee_name"].strip().lower(),
                self._to_int(row["hole_number"], "hole_number", idx),
            )
            if key in seen:
                raise CommandError(
                    f"Row {idx}: duplicate tee/hole combination in CSV for "
                    f"{row['course_name']} / {row['tee_name']} / hole {row['hole_number']}"
                )
            seen.add(key)

    def _import_rows(self, rows, allow_update=False):
        created_counts = defaultdict(int)
        updated_counts = defaultdict(int)

        course_cache = {}
        tee_cache = {}
        hole_cache = {}

        for row in rows:
            club, created = Club.objects.get_or_create(
                name=row["club_name"].strip(),
                defaults={
                    "city": row["club_city"].strip(),
                    "region": row["club_region"].strip(),
                    "country": row["club_country"].strip(),
                    "postcode": row["club_postcode"].strip(),
                },
            )
            if created:
                created_counts["clubs_created"] += 1
            elif allow_update:
                changed = False
                for field, value in {
                    "city": row["club_city"].strip(),
                    "region": row["club_region"].strip(),
                    "country": row["club_country"].strip(),
                    "postcode": row["club_postcode"].strip(),
                }.items():
                    if getattr(club, field) != value:
                        setattr(club, field, value)
                        changed = True
                if changed:
                    club.save()
                    updated_counts["clubs_updated"] += 1

            course_key = (club.id, row["course_name"].strip().lower())
            if course_key not in course_cache:
                course, created = Course.objects.get_or_create(
                    club=club,
                    name=row["course_name"].strip(),
                    defaults={
                        "holes": self._to_int(row["course_holes"], "course_holes"),
                        "par_total": self._to_int(row["course_par_total"], "course_par_total"),
                    },
                )
                if created:
                    created_counts["courses_created"] += 1
                elif allow_update:
                    changed = False
                    new_holes = self._to_int(row["course_holes"], "course_holes")
                    new_par_total = self._to_int(row["course_par_total"], "course_par_total")

                    if course.holes != new_holes:
                        course.holes = new_holes
                        changed = True
                    if course.par_total != new_par_total:
                        course.par_total = new_par_total
                        changed = True

                    if changed:
                        course.save()
                        updated_counts["courses_updated"] += 1

                course_cache[course_key] = course

            course = course_cache[course_key]

            hole_key = (course.id, self._to_int(row["hole_number"], "hole_number"))
            if hole_key not in hole_cache:
                hole, created = Hole.objects.get_or_create(
                    course=course,
                    hole_number=self._to_int(row["hole_number"], "hole_number"),
                    defaults={
                        "default_par": self._to_int(row["hole_default_par"], "hole_default_par"),
                        "default_stroke_index": self._to_int(
                            row["hole_default_stroke_index"], "hole_default_stroke_index"
                        ),
                    },
                )
                if created:
                    created_counts["holes_created"] += 1
                elif allow_update:
                    changed = False
                    new_default_par = self._to_int(row["hole_default_par"], "hole_default_par")
                    new_default_si = self._to_int(
                        row["hole_default_stroke_index"], "hole_default_stroke_index"
                    )

                    if hole.default_par != new_default_par:
                        hole.default_par = new_default_par
                        changed = True
                    if hole.default_stroke_index != new_default_si:
                        hole.default_stroke_index = new_default_si
                        changed = True

                    if changed:
                        hole.save()
                        updated_counts["holes_updated"] += 1

                hole_cache[hole_key] = hole

            hole = hole_cache[hole_key]

            tee_key = (
                course.id,
                row["tee_name"].strip().lower(),
                row["tee_colour"].strip().lower(),
                row["gender_category"].strip().lower(),
            )
            if tee_key not in tee_cache:
                tee_set, created = TeeSet.objects.get_or_create(
                    course=course,
                    name=row["tee_name"].strip(),
                    defaults={
                        "colour": row["tee_colour"].strip(),
                        "gender_category": row["gender_category"].strip(),
                        "par_total": self._to_int(row["tee_par_total"], "tee_par_total"),
                        "course_rating": row["course_rating"].strip(),
                        "slope_rating": self._to_int(row["slope_rating"], "slope_rating"),
                        "sss_value": row["sss_value"].strip() or None,
                    },
                )
                if created:
                    created_counts["tee_sets_created"] += 1
                elif allow_update:
                    changed = False
                    field_map = {
                        "colour": row["tee_colour"].strip(),
                        "gender_category": row["gender_category"].strip(),
                        "par_total": self._to_int(row["tee_par_total"], "tee_par_total"),
                        "course_rating": row["course_rating"].strip(),
                        "slope_rating": self._to_int(row["slope_rating"], "slope_rating"),
                        "sss_value": row["sss_value"].strip() or None,
                    }
                    for field, value in field_map.items():
                        if getattr(tee_set, field) != value:
                            setattr(tee_set, field, value)
                            changed = True
                    if changed:
                        tee_set.save()
                        updated_counts["tee_sets_updated"] += 1

                tee_cache[tee_key] = tee_set

            tee_set = tee_cache[tee_key]

            tee_hole_defaults = {
                "yardage": self._to_int(row["tee_yardage"], "tee_yardage"),
                "par": self._to_int(row["tee_par"], "tee_par"),
                "stroke_index": self._to_int(row["tee_stroke_index"], "tee_stroke_index"),
            }

            tee_set_hole, created = TeeSetHole.objects.get_or_create(
                tee_set=tee_set,
                hole=hole,
                defaults=tee_hole_defaults,
            )
            if created:
                created_counts["tee_set_holes_created"] += 1
            elif allow_update:
                changed = False
                for field, value in tee_hole_defaults.items():
                    if getattr(tee_set_hole, field) != value:
                        setattr(tee_set_hole, field, value)
                        changed = True
                if changed:
                    tee_set_hole.save()
                    updated_counts["tee_set_holes_updated"] += 1

        return {**created_counts, **updated_counts}

    @staticmethod
    def _to_int(value, field_name, row_num=None):
        try:
            return int(str(value).strip())
        except Exception as e:
            location = f"Row {row_num}: " if row_num else ""
            raise ValueError(f"{location}{field_name} must be an integer, got {value!r}") from e

    @staticmethod
    def _to_decimal_str(value, field_name, row_num=None):
        try:
            # validates decimal-ish string without forcing float storage
            float(str(value).strip())
            return str(value).strip()
        except Exception as e:
            location = f"Row {row_num}: " if row_num else ""
            raise ValueError(f"{location}{field_name} must be numeric, got {value!r}") from e