# Unit test for CUNYCourse
import argparse

from cuny_course import CUNYCourse

# Ask for a course id and display results of class methods
parser = argparse.ArgumentParser('Test CUNYCourse class')
parser.add_argument('-d', '--debug', action= 'store_true')
parser.add_argument('course_id', type=int)
args = parser.parse_args()

print('\nTEST SUPPLIED COURSE ID\n=======================')
course = CUNYCourse(args.course_id)
if course:
  print(course.course_id)
  print(course.institution)
  print(course.is_active)
  print(course)
  print(course.attributes)
else:
  print(course_id, 'is not in the catalog')

print('\nTEST MISSING COURSE ID\n===================')
course = CUNYCourse(0)
if course:
  print(course.course_id)
  print(course.institution)
  print(course.is_active)
  print(course)
else:
  print(course_id, 'is not in the catalog')

print('\nTEST INVALID COURSE ID\n======================')
course = CUNYCourse(str(args.course_id) + 'x')
if course:
  print(course.course_id)
  print(course.institution)
  print(course.is_active)
  print(course)
else:
  print(course_id, 'is not in the catalog')

