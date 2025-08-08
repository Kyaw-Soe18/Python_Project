from .models import Course
from collections import OrderedDict
from attendance.models import Course

from django.db.models import Min
from .models import Student, Course
from unicodedata import category
from aiohttp import request
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
from attendance.models import Attendance, UserProfile,Course, Department,Student, Class, ClassStudent

from attendance.forms import UserRegistration, UpdateProfile, UpdateProfileMeta, UpdateProfileAvatar, AddAvatar, SaveDepartment, SaveCourse, SaveClass, SaveStudent, SaveClassStudent, UpdatePasswords, UpdateFaculty

deparment_list = Department.objects.exclude(status = 2).all()
context = {
    'page_title' : 'Simple Blog Site',
    'deparment_list' : deparment_list,
    'deparment_list_limited' : deparment_list[:3]
}
#login
def login_user(request):
    logout(request)
    resp = {"status":'failed','msg':''}
    username = ''
    password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status']='success'
            else:
                resp['msg'] = "Incorrect username or password"
        else:
            resp['msg'] = "Incorrect username or password"
    return HttpResponse(json.dumps(resp),content_type='application/json')

#Logout
def logoutuser(request):
    logout(request)
    return redirect('/')

@login_required
def home(request):
    context['page_title'] = 'Home'
    departments = Department.objects.count()
    courses = Course.objects.count()
    faculty = UserProfile.objects.filter(user_type=2).count()

    if request.user.profile.user_type == 1:
        # Admin
        students = Student.objects.count()
        classes = Class.objects.count()
    else:
        # Faculty logic that matches student view
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        faculty_courses = faculty_classes.values_list('course_id', flat=True).distinct()

        # ✅ EXACTLY like your student() view logic:
        students = Student.objects.filter(course_id__in=faculty_courses).count()

        classes = faculty_classes.count()

    context['departments'] = departments
    context['courses'] = courses
    context['faculty'] = faculty
    context['students'] = students
    context['classes'] = classes

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
                profile = UserProfile.objects.get(user = newUser)
            except:
                profile = None
            if profile is None:
                UserProfile(user = newUser, dob= data['dob'], contact= data['contact'], address= data['address'], avatar = request.FILES['avatar']).save()
            else:
                UserProfile.objects.filter(id = profile.id).update(user = newUser, dob= data['dob'], contact= data['contact'], address= data['address'])
                avatar = AddAvatar(request.POST,request.FILES, instance = profile)
                if avatar.is_valid():
                    avatar.save()
            username = form.cleaned_data.get('username')
            pwd = form.cleaned_data.get('password1')
            loginUser = authenticate(username= username, password = pwd)
            login(request, loginUser)
            return redirect('home-page')
        else:
            context['reg_form'] = form

    return render(request,'register.html',context)

@login_required
def profile(request):
    context = {
        'page_title':"My Profile"
    }

    return render(request,'profile.html',context)
    
@login_required
def update_profile(request):
    context['page_title'] = "Update Profile"
    user = User.objects.get(id= request.user.id)
    profile = UserProfile.objects.get(user= user)
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
                messages.success(request,"Your Profile has been updated successfully")
                return redirect("profile")
            else:
                # form = UpdateProfile(instance=user)
                context['form2'] = form2
        else:
            context['form1'] = form
            form = UpdateProfile(instance=request.user)
    return render(request,'update_profile.html',context)


@login_required
def update_avatar(request):
    context['page_title'] = "Update Avatar"
    user = User.objects.get(id= request.user.id)
    context['userData'] = user
    context['userProfile'] = user.profile
    if user.profile.avatar:
        img = user.profile.avatar.url
    else:
        img = MEDIA_URL+"/default/default-avatar.png"

    context['img'] = img
    if request.method == 'POST':
        form = UpdateProfileAvatar(request.POST, request.FILES,instance=user)
        if form.is_valid():
            form.save()
            messages.success(request,"Your Profile has been updated successfully")
            return redirect("profile")
        else:
            context['form'] = form
            form = UpdateProfileAvatar(instance=user)
    return render(request,'update_avatar.html',context)

@login_required
def update_password(request):
    context['page_title'] = "Update Password"
    if request.method == 'POST':
        form = UpdatePasswords(user = request.user, data= request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Your Account Password has been updated successfully")
            update_session_auth_hash(request, form.user)
            return redirect("profile")
        else:
            context['form'] = form
    else:
        form = UpdatePasswords(request.POST)
        context['form'] = form
    return render(request,'update_password.html',context)

#Department
@login_required
def department(request):
    departments = Department.objects.all()
    context['page_title'] = "Department Management"
    context['departments'] = departments
    return render(request, 'department_mgt.html',context)

@login_required
def manage_department(request,pk=None):
    # department = department.objects.all()
    if pk == None:
        department = {}
    elif pk > 0:
        department = Department.objects.filter(id=pk).first()
    else:
        department = {}
    context['page_title'] = "Manage Department"
    context['department'] = department

    return render(request, 'manage_department.html',context)

@login_required
def save_department(request):
    resp = { 'status':'failed' , 'msg' : '' }
    if request.method == 'POST':
        department = None
        print(not request.POST['id'] == '')
        if not request.POST['id'] == '':
            department = Department.objects.filter(id=request.POST['id']).first()
        if not department == None:
            form = SaveDepartment(request.POST,instance = department)
        else:
            form = SaveDepartment(request.POST)
    if form.is_valid():
        form.save()
        resp['status'] = 'success'
        messages.success(request, 'Department has been saved successfully')
    else:
        for field in form:
            for error in field.errors:
                resp['msg'] += str(error + '<br>')
        if not department == None:
            form = SaveDepartment(instance = department)
       
    return HttpResponse(json.dumps(resp),content_type="application/json")

@login_required
def delete_department(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            department = Department.objects.filter(id = id).first()
            department.delete()
            resp['status'] = 'success'
            messages.success(request,'Department has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")


#Course
@login_required
def course(request):
    courses = Course.objects.all()
    context['page_title'] = "Course Management"
    context['courses'] = courses
    return render(request, 'course_mgt.html',context)

@login_required
def manage_course(request,pk=None):
    # course = course.objects.all()
    if pk == None:
        course = {}
        department = Department.objects.filter(status=1).all()
    elif pk > 0:
        course = Course.objects.filter(id=pk).first()
        department = Department.objects.filter(Q(status=1) or Q(id = course.id)).all()
    else:
        department = Department.objects.filter(status=1).all()
        course = {}
    context['page_title'] = "Manage Course"
    context['departments'] = department
    context['course'] = course

    return render(request, 'manage_course.html',context)

@login_required
def save_course(request):
    resp = { 'status':'failed' , 'msg' : '' }
    if request.method == 'POST':
        course = None
        print(not request.POST['id'] == '')
        if not request.POST['id'] == '':
            course = Course.objects.filter(id=request.POST['id']).first()
        if not course == None:
            form = SaveCourse(request.POST,instance = course)
        else:
            form = SaveCourse(request.POST)
    if form.is_valid():
        form.save()
        resp['status'] = 'success'
        messages.success(request, 'Course has been saved successfully')
    else:
        for field in form:
            for error in field.errors:
                resp['msg'] += str(error + '<br>')
        if not course == None:
            form = SaveCourse(instance = course)
       
    return HttpResponse(json.dumps(resp),content_type="application/json")

@login_required
def delete_course(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            course = Course.objects.filter(id = id).first()
            course.delete()
            resp['status'] = 'success'
            messages.success(request,'Course has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")

#Faculty
@login_required
def faculty(request):
    user = UserProfile.objects.filter(user_type = 2).all()
    context['page_title'] = "Faculty Management"
    context['faculties'] = user
    return render(request, 'faculty_mgt.html',context)

@login_required
def manage_faculty(request,pk=None):
    if pk == None:
        faculty = {}
        department = Department.objects.filter(status=1).all()
    elif pk > 0:
        faculty = UserProfile.objects.filter(id=pk).first()
        department = Department.objects.filter(Q(status=1) or Q(id = faculty.id)).all()
    else:
        department = Department.objects.filter(status=1).all()
        faculty = {}
    context['page_title'] = "Manage Faculty"
    context['departments'] = department
    context['faculty'] = faculty
    return render(request, 'manage_faculty.html',context)

@login_required
def view_faculty(request,pk=None):
    if pk == None:
        faculty = {}
    elif pk > 0:
        faculty = UserProfile.objects.filter(id=pk).first()
    else:
        faculty = {}
    context['page_title'] = "Manage Faculty"
    context['faculty'] = faculty
    return render(request, 'faculty_details.html',context)

@login_required
def save_faculty(request):
    resp = { 'status' : 'failed', 'msg' : '' }
    if request.method == 'POST':
        data = request.POST.copy()
        data.pop('last_name', None)
        if data['id'].isnumeric() and data['id'] != '':
            user = User.objects.get(id = data['id'])
        else:
            user = None
        if not user == None:
            form = UpdateFaculty(data = data, user = user, instance = user)
        else:
            form = UserRegistration(data)
        if form.is_valid():
            form.save()

            if user == None:
                user = User.objects.all().last()
            try:
                profile = UserProfile.objects.get(user = user)
            except:
                profile = None
            if profile is None:
                form2 = UpdateProfileMeta(request.POST,request.FILES)
            else:
                form2 = UpdateProfileMeta(request.POST,request.FILES, instance = profile)
                if form2.is_valid():
                    form2.save()
                    resp['status'] = 'success'
                    messages.success(request,'Faculty has been save successfully.')
                else:
                    User.objects.filter(id=user.id).delete()
                    for field in form2:
                        for error in field.errors:
                            resp['msg'] += str(error + '<br>')
            
        else:
            for field in form:
                for error in field.errors:
                    resp['msg'] += str(error + '<br>')

    return HttpResponse(json.dumps(resp),content_type='application/json')

@login_required
def delete_faculty(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            faculty = User.objects.filter(id = id).first()
            faculty.delete()
            resp['status'] = 'success'
            messages.success(request,'Faculty has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")


    
#Class
@login_required
def classPage(request):
    if request.user.profile.user_type == 1:
        classes = Class.objects.select_related('assigned_faculty__user', 'course').all()
    else:
        classes = Class.objects.select_related('assigned_faculty__user', 'course').filter(assigned_faculty=request.user.profile).all()
    context = {}
    context['page_title'] = "Class Management"
    context['classes'] = classes
    return render(request, 'class_mgt.html',context)

@login_required
def manage_class(request,pk=None):
    faculty = UserProfile.objects.filter(user_type=2).all()

    # Deduplicate courses by name
    unique_course_ids = (
        Course.objects.filter(status=1)
        .values('name')
        .annotate(id=Min('id'))
        .values_list('id', flat=True)
    )
    unique_courses = Course.objects.filter(id__in=unique_course_ids).order_by('name')

    _class = Class.objects.filter(id=pk).first() if pk else {}

    context = {
        'page_title': "Manage Class",
        'faculties': faculty,
        'courses': unique_courses,
        'class': _class,
    }

    return render(request, 'manage_class.html', context)

@login_required
def view_class(request, pk= None):
    if pk is None:
        return redirect('home-page')
    else:
        _class = Class.objects.filter(id=pk).first()
        students = ClassStudent.objects.filter(classIns = _class).all()
        context['class'] = _class
        context['students'] = students
        context['page_title'] = "Class Information"
    return render(request, 'class_details.html',context)


@login_required
def save_class(request):
    resp = {'status': 'failed', 'msg': ''}

    if request.method == 'POST':
        class_id = request.POST.get('id')
        name = request.POST.get('name')
        level = request.POST.get('level')
        school_year = request.POST.get('school_year')
        course_id = request.POST.get('course')
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
            _class.assigned_faculty = faculty

            _class.save()
            resp['status'] = 'success'
            messages.success(request, 'Class has been saved successfully')
        except Exception as e:
            resp['msg'] = str(e)

    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def delete_class(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            _class = Class.objects.filter(id = id).first()
            _class.delete()
            resp['status'] = 'success'
            messages.success(request,'Class has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")

@login_required
def manage_class_student(request,classPK = None):
    if classPK is None:
        return HttpResponse('Class ID is Unknown')
    else:
        context['classPK'] = classPK
        _class  = Class.objects.get(id = classPK)
        # print(ClassStudent.objects.filter(classIns = _class))
        students = Student.objects.exclude(id__in = ClassStudent.objects.filter(classIns = _class).values_list('student').distinct()).all()
        context['students'] = students
        return render(request, 'manage_class_student.html',context)
@login_required
def save_class_student(request):
    resp = {'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        form = SaveClassStudent(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Student has been added successfully.")
            resp['status'] = 'success'
        else:
            for field in form:
                for error in field.errors:
                    resp['msg'] += str(error+"<br>")
    return HttpResponse(json.dumps(resp),content_type = 'json')

@login_required
def delete_class_student(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            cs = ClassStudent.objects.filter(id = id).first()
            cs.delete()
            resp['status'] = 'success'
            messages.success(request,'Student has been deleted from Class successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")


#Student
@login_required
def student(request):
    context['page_title'] = "Student Management"

    if request.user.profile.user_type == 1:
        # Admin sees all students
        students = Student.objects.select_related('course').all()
    else:
        # Faculty: show only students for their assigned course(s)
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        faculty_courses = faculty_classes.values_list('course_id', flat=True).distinct()
        students = Student.objects.select_related('course').filter(course_id__in=faculty_courses)

    # Optional: For displaying course names in dropdowns or filters
    unique_course_ids = (
        Course.objects.filter(status=1)
        .values('name')
        .annotate(id=Min('id'))
        .values_list('id', flat=True)
    )
    courses = Course.objects.filter(id__in=unique_course_ids).order_by('name')

    context['students'] = students
    context['courses'] = courses
    return render(request, 'student_mgt.html', context)


@login_required
def manage_student(request, pk=None):
    context = {}
    student = Student.objects.filter(id=pk).first() if pk else None

    unique_course_ids = Course.objects.filter(status=1).values('name').annotate(id=Min('id')).values_list('id',
                                                                                                          flat=True)
    unique_courses = Course.objects.filter(id__in=unique_course_ids).order_by('name')

    context.update({
        'page_title': "Manage Student",
        'courses': unique_courses,
        'student': student,
    })

    return render(request, 'manage_student.html', context)

@login_required
def view_student(request,pk=None):
    if pk == None:
        student = {}
    elif pk > 0:
        student = Student.objects.filter(id=pk).first()
    else:
        student = {}
    context['student'] = student
    return render(request, 'student_details.html',context)


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
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            student = Student.objects.filter(id = id).first()
            student.delete()
            resp['status'] = 'success'
            messages.success(request,'Student Details has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")

#Attendance
@login_required
def attendance_class(request):
    if request.user.profile.user_type == 1:
        classes = Class.objects.all()
    else:
        classes = Class.objects.filter(assigned_faculty = request.user.profile).all()
    context['page_title'] = "Attendance Management"
    context['classes'] = classes
    return render(request, 'attendance_class.html',context)


@login_required
def attendance(request,classPK = None, date=None):
    _class = Class.objects.get(id = classPK)
    students = Student.objects.filter(id__in = ClassStudent.objects.filter(classIns = _class).values_list('student')).all()
    context['page_title'] = "Attendance Management"
    context['class'] = _class
    context['date'] = date
    att_data = {}
    for student in students:
        att_data[student.id] = {}
        att_data[student.id]['data'] = student
    if not date is None:
        date = datetime.strptime(date, '%Y-%m-%d')
        year = date.strftime('%Y')
        month = date.strftime('%m')
        day = date.strftime('%d')
        attendance = Attendance.objects.filter(attendance_date__year = year, attendance_date__month = month, attendance_date__day = day, classIns = _class).all()
        for att in attendance:
            att_data[att.student.pk]['type'] = att.type
    print(list(att_data.values()))
    context['att_data'] = list(att_data.values())
    context['students'] = students

    return render(request, 'attendance_mgt.html',context)

@login_required
def save_attendance(request):
    resp = {'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        post = request.POST
        date = datetime.strptime(post['attendance_date'], '%Y-%m-%d')
        year = date.strftime('%Y')
        month = date.strftime('%m')
        day = date.strftime('%d')
        _class = Class.objects.get(id=post['classIns'])
        Attendance.objects.filter(attendance_date__year = year, attendance_date__month = month, attendance_date__day = day,classIns = _class).delete()
        for student in post.getlist('student[]'):
            type = post['type['+student+']']
            studInstance = Student.objects.get(id = student)
            att = Attendance(student=studInstance,type = type,classIns = _class,attendance_date=post['attendance_date']).save()
        resp['status'] = 'success'
        messages.success(request,"Attendance has been saved successfully.")
    return HttpResponse(json.dumps(resp),content_type="application/json")