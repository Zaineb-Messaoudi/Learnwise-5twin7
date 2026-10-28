import os
import re

frontend = 'C:/Users/ASUS/Downloads/django/learnwise-frontend/src'

# Count CSS imports
css_imports = 0
jsx_files = 0
for root, dirs, files in os.walk(frontend):
    for f in files:
        if f.endswith('.jsx'):
            jsx_files += 1
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
                if re.search(r"import\s+['\"]\.\./components/courses\.css['\"]", content):
                    css_imports += 1

print(f'JSX files: {jsx_files}')
print(f'Components with CSS import: {css_imports}')

# Check specific components
components_to_check = [
    'features/student/components/CourseCard.jsx',
    'features/student/components/CourseFilters.jsx',
    'features/student/components/LessonNavigator.jsx',
    'features/instructor/components/CourseMaterialUpload.jsx',
    'features/student/pages/CoursesPage.jsx',
    'features/student/pages/CourseDetailPage.jsx',
    'features/admin/pages/CourseModerationPage.jsx',
    'features/teacher/pages/CourseCreatePage.jsx',
    'features/teacher/pages/CourseEditPage.jsx',
    'features/teacher/pages/CourseChaptersPage.jsx',
    'features/teacher/pages/CourseVersionsPage.jsx',
    'features/teacher/pages/CourseSchedulePage.jsx',
    'features/teacher/pages/CoursePrerequisitesPage.jsx',
    'features/teacher/pages/CourseExportPage.jsx',
]

print()
for comp in components_to_check:
    path = os.path.join(frontend, comp)
    if os.path.exists(path):
        with open(path) as fh:
            content = fh.read()
        has_import = bool(re.search(r"import\s+['\"]\.\./components/courses\.css['\"]", content))
        print(f'  {comp}: {\"✅\" if has_import else \"❌\"} CSS import')
    else:
        print(f'  {comp}: ❌ Not found')