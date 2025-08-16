from django.contrib import admin
from .models import Department, Course, Student,UserProfile, Class, SectionSchedule, SectionDailyAttendance

# Register your models here.


admin.site.register(UserProfile)
admin.site.register(Department)
admin.site.register(Course)
admin.site.register(Class)
admin.site.register(Student)
admin.site.register(SectionSchedule)
admin.site.register(SectionDailyAttendance)

