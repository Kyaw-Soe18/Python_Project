from .models import Course
from collections import OrderedDict
from attendance.models import Course

from django.db.models import Min
from .models import Student, Course
from unicodedata import category
# from aiohttp import request
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from ams.settings import MEDIA_ROOT, MEDIA_URL
from attendance.models import UserProfile, Course, Department, Student, Class

from attendance.forms import UserRegistration, UpdateProfile, UpdateProfileMeta, UpdateProfileAvatar, AddAvatar, \
    SaveDepartment, SaveCourse, SaveClass, SaveStudent, UpdatePasswords, UpdateFaculty
from django.http import JsonResponse
from attendance.models import Section
from .models import Section
from django.db import transaction
from datetime import date as _date, datetime as _datetime, timedelta
from calendar import monthrange
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404

# ❗️ Adjust these imports to your project structure if needed
from .models import SectionSchedule, SectionDailyAttendance, SectionDailyAttendanceDetail
from attendance.models import Section, Student, UserProfile  # if these live elsewhere, change path
from .forms import SectionScheduleForm

from decimal import Decimal
from datetime import date as _date, datetime as _datetime
from django.shortcuts import render, redirect
from django.contrib import messages

from django.db.models import Q, Min

deparment_list = Department.objects.exclude(status=2).all()
context = {
    'page_title': '',
    'deparment_list': deparment_list,
    'deparment_list_limited': deparment_list[:3]
}


@login_required
def ajax_load_sections(request):
    course_id = request.GET.get('course_id')
    sections = []
    if course_id:
        sections = Section.objects.filter(course_id=course_id).values('id', 'name')
    return JsonResponse({'sections': list(sections)})


# login
def login_user(request):
    logout(request)
    resp = {"status": 'failed', 'msg': ''}
    username = ''
    password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status'] = 'success'
            else:
                resp['msg'] = "Incorrect username or password"
        else:
            resp['msg'] = "Incorrect username or password"
    return HttpResponse(json.dumps(resp), content_type='application/json')


# Logout
def logoutuser(request):
    logout(request)
    return redirect('/')

@login_required
def home(request):
    context = {}
    context['page_title'] = 'Home'

    # Count departments and courses
    departments = Department.objects.count()
    courses = Course.objects.count()

    # Count Teachers + Coordinators
    teacher_count = UserProfile.objects.filter(user_type=2).count()
    coordinator_count = UserProfile.objects.filter(user_type=3).count()
    total_faculty = teacher_count + coordinator_count

    # Count students and classes based on user type
    if request.user.profile.user_type == 1:
        # Admin: count everything
        students = Student.objects.count()
        classes = Class.objects.count()
    else:
        # Faculty (teacher/coordinator)
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)

        # Get sections the faculty is assigned to
        faculty_sections = faculty_classes.values_list('section_id', flat=True).distinct()

        # Only count students from those sections
        students = Student.objects.filter(section_id__in=faculty_sections).count()

        classes = faculty_classes.count()

    # Update context
    context.update({
        'departments': departments,
        'courses': courses,
        'faculty': total_faculty,  # <-- updated
        'students': students,
        'classes': classes,
    })

    return render(request, 'home.html', context)

def registerUser(request):
    user = request.user
    if user.is_authenticated:
        return redirect('home-page')
    context['page_title'] = "Register User"
    if request.method == 'POST':
        data = request.POST
        form = UserRegistration(data)
        if form.is_valid():
            form.save()
            newUser = User.objects.all().last()
            try:
                profile = UserProfile.objects.get(user=newUser)
            except:
                profile = None
            if profile is None:
                UserProfile(user=newUser, dob=data['dob'], contact=data['contact'], address=data['address'],
                            avatar=request.FILES['avatar']).save()
            else:
                UserProfile.objects.filter(id=profile.id).update(user=newUser, dob=data['dob'], contact=data['contact'],
                                                                 address=data['address'])
                avatar = AddAvatar(request.POST, request.FILES, instance=profile)
                if avatar.is_valid():
                    avatar.save()
            username = form.cleaned_data.get('username')
            pwd = form.cleaned_data.get('password1')
            loginUser = authenticate(username=username, password=pwd)
            login(request, loginUser)
            return redirect('home-page')
        else:
            context['reg_form'] = form

    return render(request, 'register.html', context)


@login_required
def profile(request):
    context = {
        'page_title': "My Profile"
    }

    return render(request, 'profile.html', context)


@login_required
def update_profile(request):
    context['page_title'] = "Update Profile"
    user = User.objects.get(id=request.user.id)
    profile = UserProfile.objects.get(user=user)
    context['userData'] = user
    context['userProfile'] = profile
    if request.method == 'POST':
        data = request.POST
        # if data['password1'] == '':
        # data['password1'] = '123'
        form = UpdateProfile(data, instance=user)
        if form.is_valid():
            form.save()
            form2 = UpdateProfileMeta(data, instance=profile)
            if form2.is_valid():
                form2.save()
                messages.success(request, "Your Profile has been updated successfully")
                return redirect("profile")
            else:
                # form = UpdateProfile(instance=user)
                context['form2'] = form2
        else:
            context['form1'] = form
            form = UpdateProfile(instance=request.user)
    return render(request, 'update_profile.html', context)


@login_required
def update_avatar(request):
    context['page_title'] = "Update Avatar"
    user = User.objects.get(id=request.user.id)
    context['userData'] = user
    context['userProfile'] = user.profile
    if user.profile.avatar:
        img = user.profile.avatar.url
    else:
        img = MEDIA_URL + "/default/default-avatar.png"

    context['img'] = img
    if request.method == 'POST':
        form = UpdateProfileAvatar(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your Profile has been updated successfully")
            return redirect("profile")
        else:
            context['form'] = form
            form = UpdateProfileAvatar(instance=user)
    return render(request, 'update_avatar.html', context)


@login_required
def update_password(request):
    context['page_title'] = "Update Password"
    if request.method == 'POST':
        form = UpdatePasswords(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your Account Password has been updated successfully")
            update_session_auth_hash(request, form.user)
            return redirect("profile")
        else:
            context['form'] = form
    else:
        form = UpdatePasswords(request.POST)
        context['form'] = form
    return render(request, 'update_password.html', context)


# Faculty
@login_required
def department(request):
    departments = Department.objects.all()
    context['page_title'] = "Faculty Management"
    context['departments'] = departments
    return render(request, 'department_mgt.html', context)


@login_required
def manage_department(request, pk=None):
    # department = department.objects.all()
    if pk == None:
        department = {}
    elif pk > 0:
        department = Department.objects.filter(id=pk).first()
    else:
        department = {}
    context['page_title'] = "Manage Faculty"
    context['department'] = department

    return render(request, 'manage_department.html', context)


@login_required
def save_department(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        department = None
        print(not request.POST['id'] == '')
        if not request.POST['id'] == '':
            department = Department.objects.filter(id=request.POST['id']).first()
        if not department == None:
            form = SaveDepartment(request.POST, instance=department)
        else:
            form = SaveDepartment(request.POST)
    if form.is_valid():
        form.save()
        resp['status'] = 'success'
        messages.success(request, 'Faculty has been saved successfully')
    else:
        for field in form:
            for error in field.errors:
                resp['msg'] += str(error + '<br>')
        if not department == None:
            form = SaveDepartment(instance=department)

    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
def delete_department(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            department = Department.objects.filter(id=id).first()
            department.delete()
            resp['status'] = 'success'
            messages.success(request, 'Faculty has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp), content_type="application/json")


# Course
@login_required
def course(request):
    courses = Course.objects.all()
    context['page_title'] = "Major Management"
    context['courses'] = courses
    return render(request, 'course_mgt.html', context)


@login_required
def manage_course(request, pk=None):
    context = {}
    try:
        if pk is None:
            course = {}
            department = Department.objects.filter(status=1).all()
            section_names = ''
        elif pk > 0:
            course = Course.objects.filter(id=pk).first()
            department = Department.objects.filter(
                Q(status=1) | Q(id=course.department_id if course and course.department else 0)
            ).all()
            if course:
                section_names = ', '.join(course.sections.values_list('name', flat=True))
            else:
                section_names = ''
        else:
            department = Department.objects.filter(status=1).all()
            course = {}
            section_names = ''

        context['page_title'] = "Manage Course"
        context['departments'] = department
        context['course'] = course
        context['section_names'] = section_names

        return render(request, 'manage_course.html', context)
    except Exception as e:
        import traceback
        print("ERROR in manage_course:", e)
        traceback.print_exc()
        raise


@login_required
def save_course(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        with transaction.atomic():
            course = None
            if request.POST.get('id'):
                course = Course.objects.filter(id=request.POST['id']).first()

            if course:
                form = SaveCourse(request.POST, instance=course)
            else:
                form = SaveCourse(request.POST)

            if form.is_valid():
                saved_course = form.save()

                section_names_str = request.POST.get('section_names', '').strip()
                # Normalize and split section names by comma
                section_names = [name.strip() for name in section_names_str.split(',') if name.strip()]

                # Existing sections linked to this course
                existing_sections = saved_course.sections.all()

                # Delete sections no longer in the list
                for sec in existing_sections:
                    if sec.name not in section_names:
                        sec.delete()

                # Add or update sections
                for name in section_names:
                    section_obj, created = Section.objects.get_or_create(course=saved_course, name=name)

                resp['status'] = 'success'
                messages.success(request, 'Course has been saved successfully')
            else:
                for field in form:
                    for error in field.errors:
                        resp['msg'] += str(error + '<br>')
    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
def delete_course(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            course = Course.objects.filter(id=id).first()
            course.delete()
            resp['status'] = 'success'
            messages.success(request, 'Course has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp), content_type="application/json")


# Faculty Staff
@login_required
def faculty(request):
    user = UserProfile.objects.filter(Q(user_type=2) | Q(user_type=3)).all()
    context['page_title'] = "Faculty Staff Management"
    context['faculties'] = user
    return render(request, 'faculty_mgt.html', context)


@login_required
def manage_faculty(request, pk=None):
    if pk == None:
        faculty = {}
        department = Department.objects.filter(status=1).all()
    elif pk > 0:
        faculty = UserProfile.objects.filter(id=pk).first()
        department = Department.objects.filter(Q(status=1) or Q(id=faculty.id)).all()
    else:
        department = Department.objects.filter(status=1).all()
        faculty = {}
    context['page_title'] = "Manage Faculty Staff"
    context['departments'] = department
    context['faculty'] = faculty
    return render(request, 'manage_faculty.html', context)


@login_required
def view_faculty(request, pk=None):
    if pk == None:
        faculty = {}
    elif pk > 0:
        faculty = UserProfile.objects.filter(id=pk).first()
    else:
        faculty = {}
    context['page_title'] = "Manage Faculty Staff"
    context['faculty'] = faculty
    return render(request, 'faculty_details.html', context)


@login_required
def save_faculty(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        data = request.POST.copy()
        data.pop('last_name', None)

        # Get user if updating
        if data['id'].isnumeric() and data['id'] != '':
            user = User.objects.get(id=data['id'])
        else:
            user = None

        # Create or update User
        if user:
            form = UpdateFaculty(data=data, user=user, instance=user)
        else:
            form = UserRegistration(data)

        if form.is_valid():
            form.save()

            if user is None:
                user = User.objects.all().last()

            try:
                profile = UserProfile.objects.get(user=user)
            except:
                profile = None

            if profile is None:
                form2 = UpdateProfileMeta(request.POST, request.FILES)
            else:
                form2 = UpdateProfileMeta(request.POST, request.FILES, instance=profile)

            if form2.is_valid():
                # ✅ Save profile normally
                saved_profile = form2.save(commit=False)
                # ✅ Force user_type from dropdown instead of default=2
                saved_profile.user_type = int(request.POST.get("user_type", 2))
                saved_profile.save()

                resp['status'] = 'success'
                messages.success(request, 'Faculty Staff has been saved successfully.')
            else:
                # Rollback user if profile fails
                if not profile:
                    User.objects.filter(id=user.id).delete()
                for field in form2:
                    for error in field.errors:
                        resp['msg'] += str(error + '<br>')
        else:
            for field in form:
                for error in field.errors:
                    resp['msg'] += str(error + '<br>')

    return HttpResponse(json.dumps(resp), content_type='application/json')


@login_required
def delete_faculty(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            faculty = User.objects.filter(id=id).first()
            faculty.delete()
            resp['status'] = 'success'
            messages.success(request, 'Faculty has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp), content_type="application/json")


# Class
@login_required
def classPage(request):
    if request.user.profile.user_type == 1:
        classes = Class.objects.select_related('assigned_faculty__user', 'course').all()
    else:
        classes = Class.objects.select_related('assigned_faculty__user', 'course').filter(
            assigned_faculty=request.user.profile).all()
    context = {}
    context['page_title'] = "Class Management"
    context['classes'] = classes
    return render(request, 'class_mgt.html', context)


@login_required
def manage_class(request, pk=None):
    faculty = UserProfile.objects.filter(Q(user_type=2) | Q(user_type=3)).all()

    # Deduplicate courses by name
    unique_course_ids = (
        Course.objects.filter(status=1)
        .values('name')
        .annotate(id=Min('id'))
        .values_list('id', flat=True)
    )
    unique_courses = Course.objects.filter(id__in=unique_course_ids).order_by('name')

    _class = Class.objects.filter(id=pk).first() if pk else {}
    # All classes for listing in table, select_related to avoid extra queries
    classes = Class.objects.select_related('assigned_faculty', 'course', 'section').all()
    context = {
        'page_title': "Manage Class",
        'faculties': faculty,
        'courses': unique_courses,
        'class': _class,
        'classes': classes,  # ✅ send all classes
    }

    return render(request, 'manage_class.html', context)


@login_required
def save_class(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        class_id = request.POST.get('id')
        name = request.POST.get('name')
        level = request.POST.get('level')
        school_year = request.POST.get('school_year')
        course_id = request.POST.get('course')
        section_id = request.POST.get('section')  # Add this line

        faculty_id = request.POST.get('assigned_faculty')

        try:
            course = Course.objects.get(id=course_id) if course_id else None
            faculty = UserProfile.objects.get(id=faculty_id) if faculty_id else None

            if class_id:
                _class = Class.objects.get(id=class_id)
            else:
                _class = Class()

            _class.name = name
            _class.level = level
            _class.school_year = school_year
            _class.course = course
            _class.section = Section.objects.get(id=section_id) if section_id else None
            _class.assigned_faculty = faculty

            _class.save()
            resp['status'] = 'success'
            messages.success(request, 'Class has been saved successfully')
        except Exception as e:
            resp['msg'] = str(e)

    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
def delete_class(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            _class = Class.objects.filter(id=id).first()
            _class.delete()
            resp['status'] = 'success'
            messages.success(request, 'Class has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp), content_type="application/json")

# Student
@login_required
def student(request):
    context = {}
    context['page_title'] = "Student Management"

    if request.user.profile.user_type == 1:  # Admin
        students = Student.objects.select_related('course', 'section').all()
        courses = Course.objects.filter(status=1).order_by('name')
        sections = Section.objects.filter(course__in=courses).order_by('course__name', 'name')
    else:  # Faculty
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        faculty_courses = Course.objects.filter(id__in=faculty_classes.values_list('course_id', flat=True))
        faculty_sections = Section.objects.filter(id__in=faculty_classes.values_list('section_id', flat=True))

        students = Student.objects.select_related('course', 'section').filter(section__in=faculty_sections)
        courses = faculty_courses
        sections = faculty_sections.order_by('name')

    # Build sections_by_course dict
    sections_by_course = {}
    for section in sections:
        course_name = section.course.name
        if course_name not in sections_by_course:
            sections_by_course[course_name] = []
        sections_by_course[course_name].append(section.name)

    context['students'] = students
    context['courses'] = courses
    context['sections_by_course'] = sections_by_course

    return render(request, 'student_mgt.html', context)


@login_required
def manage_student(request, pk=None):
    context = {}
    student = Student.objects.filter(id=pk).first() if pk else None

    courses = Course.objects.filter(status=1).order_by('name')

    context.update({
        'page_title': "Manage Student",
        'courses': courses,
        'student': student,
    })

    return render(request, 'manage_student.html', context)


@login_required
def view_student(request, pk=None):
    if pk == None:
        student = {}
    elif pk > 0:
        student = Student.objects.filter(id=pk).first()
    else:
        student = {}
    context['student'] = student
    return render(request, 'student_details.html', context)


@login_required
def save_student(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        print("POST Data:", request.POST)
        student = None
        if request.POST.get('id') and request.POST['id'] != '':
            student = Student.objects.filter(id=request.POST['id']).first()

        # Use the existing instance if editing, or create new
        form = SaveStudent(request.POST, instance=student)

        if form.is_valid():
            form.save()
            resp['status'] = 'success'
            messages.success(request, 'Student details have been saved successfully')
        else:
            for field in form:
                for error in field.errors:
                    resp['msg'] += str(error) + '<br>'

    return HttpResponse(json.dumps(resp), content_type="application/json")


@login_required
def delete_student(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            student = Student.objects.filter(id=id).first()
            student.delete()
            resp['status'] = 'success'
            messages.success(request, 'Student Details has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp), content_type="application/json")


# ---------- helpers ----------
def _weekday_map(schedule: SectionSchedule):
    if not schedule:
        return {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    return {
        0: schedule.monday_hours,
        1: schedule.tuesday_hours,
        2: schedule.wednesday_hours,
        3: schedule.thursday_hours,
        4: schedule.friday_hours,
    }


def _expected_hours_in_month(section, year: int, month: int):
    schedule = getattr(section, 'schedule', None)
    m = _weekday_map(schedule)
    days_in_month = monthrange(year, month)[1]
    total = 0
    for d in range(1, days_in_month + 1):
        wk = _date(year, month, d).weekday()  # 0=Mon..6=Sun
        total += m.get(wk, 0)
    return total


def _attended_hours_for_student_in_month(section, student, year: int, month: int):
    qs = SectionDailyAttendance.objects.filter(
        section=section, student=student,
        date__year=year, date__month=month
    ).aggregate(total=Sum('attended_hours'))
    return float(qs['total'] or 0)


# ---------- 1) Super Admin: Section-wise schedule manage ----------
@login_required
def section_schedule_manage(request):
    """
    Dropdown နဲ့ Section ရွေး → Mon–Fri hours သတ်မှတ်/ပြင်
    """
    # super admin/staff only (change logic to your role system if needed)
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Only admin/staff can manage section schedule.")
        return redirect('home')

    sections = Section.objects.all().order_by('id')  # show all sections from DB
    section_id = request.GET.get('section') or request.POST.get('section')
    selected_section = Section.objects.filter(id=section_id).first() if section_id else None
    form = None

    if request.method == 'POST' and selected_section:
        schedule, _ = SectionSchedule.objects.get_or_create(section=selected_section)
        form = SectionScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, f"Schedule saved for Section {selected_section}.")
            return redirect(f"{request.path}?section={selected_section.id}")
    elif selected_section:
        schedule, _ = SectionSchedule.objects.get_or_create(section=selected_section)
        form = SectionScheduleForm(instance=schedule)

    return render(request, 'section_schedule_manage.html', {
        'sections': sections,
        'selected_section': selected_section,
        'form': form,
        'page_title': "Section_Schedule",
    })


# ---------- 2) Admin: Daily attendance marking (section-level) ----------
@login_required
def section_attendance_mark(request):
    """
    Section attendance:
    - Faculty (assigned) uses checkboxes
    - Coordinator/Admin can edit with numeric inputs (total hours)
    - Edited row moves to top if edited by coordinator
    """
    from datetime import datetime as _datetime, date as _date
    from django.contrib import messages

    # --- Get user profile ---
    try:
        profile = UserProfile.objects.get(user=request.user)
        faculty_dept = profile.department
    except UserProfile.DoesNotExist:
        profile = None
        faculty_dept = None

    # --- Sections for filters ---
    sections = Section.objects.none()
    assigned_sections = Section.objects.none()
    coordinator_sections = Section.objects.none()

    if request.user.is_staff or request.user.is_superuser:
        sections = Section.objects.all().order_by('id')
    elif profile and profile.user_type == 3:
        assigned_sections = Section.objects.filter(
            id__in=Class.objects.filter(assigned_faculty=profile)
                .exclude(section__isnull=True)
                .values_list('section_id', flat=True)
        ).order_by('id')
        coordinator_sections = Section.objects.filter(course__department=faculty_dept).order_by('id') if faculty_dept else Section.objects.none()
    else:
        sections = Section.objects.filter(
            id__in=Class.objects.filter(assigned_faculty=profile)
                .exclude(section__isnull=True)
                .values_list('section_id', flat=True)
        ).order_by('id')

    # --- Selected section ---
    section_id = (
        request.GET.get('assigned_section') or
        request.GET.get('coordinator_section') or
        request.GET.get('section') or
        request.POST.get('section')
    )

    the_date_str = request.GET.get('date') or request.POST.get('date')
    the_date = _date.today()
    if the_date_str:
        try:
            the_date = _datetime.strptime(the_date_str, '%Y-%m-%d').date()
        except Exception:
            pass

    selected_section = None
    selected_assigned_section = None
    selected_coordinator_section = None

    if section_id:
        try:
            section_id = int(section_id)
        except ValueError:
            section_id = None

        if profile and profile.user_type == 3:
            if request.GET.get('assigned_section'):
                selected_assigned_section = assigned_sections.filter(id=section_id).first()
                selected_section = selected_assigned_section
            elif request.GET.get('coordinator_section'):
                selected_coordinator_section = coordinator_sections.filter(id=section_id).first()
                selected_section = selected_coordinator_section
        else:
            selected_section = sections.filter(id=section_id).first()

    # --- Students and schedule ---
    students = list(Student.objects.none())
    schedule = None
    max_today = 0
    if selected_section:
        students = list(Student.objects.filter(section=selected_section).order_by('id'))
        schedule = getattr(selected_section, 'schedule', None)
        if schedule:
            wk = the_date.weekday()
            max_today = _weekday_map(schedule).get(wk, 0)

    # --- Roles ---
    is_admin = request.user.is_staff or request.user.is_superuser
    is_faculty_assigned = profile and profile.user_type == 3 and selected_assigned_section is not None
    is_faculty_coordinator = profile and profile.user_type == 3 and selected_coordinator_section is not None

    # --- Load existing attendance ---
    existing_hours = {}
    existing_details = {}
    attendances = SectionDailyAttendance.objects.filter(section=selected_section, date=the_date)
    for att in attendances:
        existing_hours[att.student_id] = int(att.attended_hours)
        existing_details[att.student_id] = list(att.details.values_list("hour", flat=True))

    # --- Get edited_student_id from GET (after redirect) ---
    edited_student_id = request.GET.get("edited_student")
    if edited_student_id:
        edited_student_id = int(edited_student_id)

    # --- Save attendance ---
    if request.method == 'POST' and selected_section:
        edited_student_id = None
        for s in students:
            if is_admin or is_faculty_coordinator:
                raw_val = request.POST.get(f"hours[{s.id}]")
                try:
                    val = int(raw_val)
                except (TypeError, ValueError):
                    val = 0
                old_val = existing_hours.get(s.id, 0)
                if val != old_val:
                    edited_student_id = s.id
            else:
                raw_vals = request.POST.getlist(f"hours[{s.id}][]")
                val = len(raw_vals)

            val = max(0, min(val, max_today))  # clamp

            # Save/update main attendance
            att, _ = SectionDailyAttendance.objects.update_or_create(
                student=s, section=selected_section, date=the_date,
                defaults={'attended_hours': val}
            )

            if is_admin or is_faculty_coordinator:
                # already saved hours for this attendance
                existing_hours_for_student = set(att.details.values_list("hour", flat=True))
                current_count = len(existing_hours_for_student)

                if val > current_count:
                    # add only the missing hours
                    for h in range(1, val + 1):
                        if h not in existing_hours_for_student:
                            SectionDailyAttendanceDetail.objects.get_or_create(
                                attendance=att,
                                hour=h
                            )
                elif val < current_count:
                    # remove the extra ones
                    att.details.filter(hour__gt=val).delete()

            else:
                # faculty still uses checkbox POST
                att.details.all().delete()
                for h in request.POST.getlist(f"hours[{s.id}][]"):
                    SectionDailyAttendanceDetail.objects.create(
                        attendance=att,
                        hour=int(h)
                    )

        messages.success(request, "Attendance saved successfully.")

        # --- Redirect with edited_student_id ---
        query_params = f"?date={the_date}"
        if selected_assigned_section:
            query_params += f"&assigned_section={selected_assigned_section.id}"
        elif selected_coordinator_section:
            query_params += f"&coordinator_section={selected_coordinator_section.id}"
        else:
            query_params += f"&section={selected_section.id}"
        if edited_student_id and is_faculty_coordinator:
            query_params += f"&edited_student={edited_student_id}"
        return redirect(f"{request.path}{query_params}")

    # --- Reorder students: move edited student first ---
    if edited_student_id and is_faculty_coordinator:
        for i, s in enumerate(students):
            if s.id == edited_student_id:
                edited_student = students.pop(i)
                students.insert(0, edited_student)
                break

    return render(request, 'section_attendance_mark.html', {
        'sections': sections,
        'assigned_sections': assigned_sections,
        'coordinator_sections': coordinator_sections,
        'selected_section': selected_section,
        'selected_assigned_section': selected_assigned_section,
        'selected_coordinator_section': selected_coordinator_section,
        'students': students,
        'date': the_date,
        'schedule': schedule,
        'max_today': max_today,
        'existing_hours': existing_hours,
        'existing_details': existing_details,
        'page_title': 'Attendance (daily)',
        'is_admin': is_admin,
        'is_faculty_assigned': is_faculty_assigned,
        'is_faculty_coordinator': is_faculty_coordinator,
    })




# ---------- 3) Faculty: Monthly roll-call % (read-only) ----------
@login_required
def section_rollcall_monthly(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        faculty_dept = profile.department
    except UserProfile.DoesNotExist:
        faculty_dept = None

    if request.user.is_staff or request.user.is_superuser or getattr(profile, 'is_coordinator', False):
        sections = Section.objects.all().order_by('id')
    else:
        sections = Section.objects.filter(course__department=faculty_dept).order_by('id')

    section_id = request.GET.get('section')
    year = int(request.GET.get('year') or _date.today().year)
    month = request.GET.get('month')
    start_month = request.GET.get('start_month')
    end_month = request.GET.get('end_month')
    min_percent = request.GET.get('min_percent', 0)
    max_percent = request.GET.get('max_percent')

    try:
        min_percent = int(min_percent)
    except (TypeError, ValueError):
        min_percent = 0

    selected_section = sections.filter(id=section_id).first() if section_id else None
    results = []

    if selected_section:
        studs = Student.objects.filter(section=selected_section).order_by('id')

        if start_month and end_month:
            month_list = list(range(int(start_month), int(end_month) + 1))
        elif month:
            month_list = [int(month)]
        else:
            month_list = [_date.today().month]

        for s in studs:
            total_attended = 0
            total_expected = 0
            for m in month_list:
                expected = _expected_hours_in_month(selected_section, year, m)
                attended = _attended_hours_for_student_in_month(selected_section, s, year, m)
                total_attended += attended
                total_expected += expected
            percent = round((total_attended / total_expected) * 100, 2) if total_expected > 0 else None

            if percent is not None:
                if min_percent and percent < float(min_percent):
                    continue
                if max_percent and percent > float(max_percent):
                    continue

            results.append({
                'student': s,
                'attended': total_attended,
                'expected': total_expected,
                'percent': percent
            })

    # Define month names for dropdown
    month_choices = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]

    return render(request, 'section_rollcall_monthly.html', {
        'sections': sections,
        'selected_section': selected_section,
        'year': year,
        'month': int(month) if month else _date.today().month,
        'start_month': int(start_month) if start_month else None,
        'end_month': int(end_month) if end_month else None,
        'min_percent': min_percent,
        'max_percent': max_percent,
        'results': results,
        'page_title': 'Monthly %',
        'month_choices': month_choices,  # pass month choices
    })
