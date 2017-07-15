# Unit test for CatalogInfo
import argparse

from cuny_catalog import CatalogInfo

# Ask for a course id and display results of class methods
parser = argparse.ArgumentParser('Test CatalogInfo class')
parser.add_argument('-d', '--debug', action= 'store_true')
parser.add_argument('course_id', type=int)
args = parser.parse_args()
course = CatalogInfo(args.course_id)
if course:
  print(course.course_id)
  print(course.institution)
  print(course.is_active)
  print(course)
else:
  print(course_id, 'is not in the catalog')

course = CatalogInfo(str(args.course_id) + 'x')
if course:
  print(course.course_id)
  print(course.institution)
  print(course.is_active)
  print(course)
else:
  print(course_id, 'is not in the catalog')

