-- Create copies of the course mapping tables for downloading.

copy (select * from program_requirements)
to '/Users/vickery/Projects/transfer_app/static/csv/program_requirements.csv'
csv header;

copy (select * from course_requirement_mappings)
to '/Users/vickery/Projects/transfer_app/static/csv/course_requirement_mappings.csv'
csv header;
