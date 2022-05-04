from django.contrib import admin

from schedule_app import forms, models


@admin.display(description='Категории')
class CategoryAdmin(admin.ModelAdmin):
    form = forms.CategoryForm
    list_display = ('name', 'work_with_peoples', 'time_coefficient', 'additional_time')
    list_filter = ('work_with_peoples',)


@admin.display(description='Типы активностей')
class ActivityTypeAdmin(admin.ModelAdmin):
    form = forms.ActivityTypeForm
    list_display = ('name',)


@admin.display(description='Общее расписание')
class ActivityOnEventAdmin(admin.ModelAdmin):
    # TODO https://realpython.com/customize-django-admin-python/#changing-how-models-are-edited
    # TODO рядом с duration отображать колонку "учетное время", куда выводить
    #  с учетом коэффициента категории и доп. времени в ней
    form = forms.ActivityOnEventForm
    list_display = ('activity', 'get_activity_type', 'event', 'start_dt', 'end_dt', 'duration')
    list_filter = ('event', 'activity__activity_type', 'activity', 'person')
    save_as = True

    @staticmethod
    @admin.display(description='Дата начала')
    def start_date_time(obj):
        return obj.start_dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    @admin.display(description='Дата окончания')
    def end_date_time(obj):
        return obj.end_dt.strftime("%Y-%m-%d %H:%M:%S")

    @admin.display(description='Тип')
    def get_activity_type(self, obj):
        return obj.activity.activity_type


@admin.display(description='Активности')
class ActivityAdmin(admin.ModelAdmin):
    form = forms.ActivityForm
    list_display = ('name', 'category', 'activity_type')

    list_filter = ('category', 'activity_type')


# class ActivitiesInline(admin.TabularInline):
#     model = models.ActivityOnEvent
#     readonly_fields = ('event',)


@admin.display(description='Люди')
class PersonAdmin(admin.ModelAdmin):
    form = forms.PersonForm
    list_display = ('first_name', 'last_name')

    # inlines = [ActivitiesInline]


@admin.display(description='Мероприятия')
class EventAdmin(admin.ModelAdmin):
    form = forms.EventForm
    list_display = ('title', 'start_date', 'end_date')
    # inlines = [ActivitiesInline]


admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.ActivityType, ActivityTypeAdmin)
admin.site.register(models.Activity, ActivityAdmin)
admin.site.register(models.Person, PersonAdmin)
admin.site.register(models.Event, EventAdmin)
admin.site.register(models.ActivityOnEvent, ActivityOnEventAdmin)
