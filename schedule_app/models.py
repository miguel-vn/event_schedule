"""
Исходник
https://docs.google.com/spreadsheets/d/1CO-mvJSt_Ui-_qv7TGWlQpMzzsw3gGVhwZj512HxaRU/edit#gid=1175281723
"""

import datetime

from django.contrib import admin
from django.db import models

import schedule_app.constants as const


class ActivityType(models.Model):
    """
    Тип активности: официальное расписание, волонтерское расписание, прочее (конкурсы, апертуры, репетиции, возлияния...)
    """

    name = models.CharField(choices=const.ACTIVITY_TYPE_CHOICES, max_length=120, default=const.VOLUNTEER)

    class Meta:
        verbose_name = 'Тип деятельности'
        verbose_name_plural = 'Типы деятельности'

    def get_events(self, pk):
        return ActivityOnEvent.objects.filter(event__pk=pk, activity__activity_type=self)

    def __str__(self):
        return self.get_name_display()


class Category(models.Model):
    name = models.CharField(max_length=120, verbose_name='Название')
    activity_type = models.ForeignKey(ActivityType, on_delete=models.CASCADE, verbose_name='Тип активности',
                                      default=0)

    work_with_peoples = models.BooleanField(default=False, verbose_name='Работа с людьми')
    time_coefficient = models.DecimalField(default=1.0, decimal_places=1, max_digits=2,
                                           blank=False,
                                           null=False,
                                           verbose_name='Временной коэффициент')
    additional_time = models.TimeField(default=datetime.time(0, 0, 0), blank=False, null=False,
                                       verbose_name='Дополнительное время')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Activity(models.Model):
    name = models.CharField(max_length=120, verbose_name='Название')
    description = models.TextField(max_length=5000, blank=True, null=True, verbose_name='Описание')

    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категория')
    need_peoples = models.IntegerField(null=True, blank=True, verbose_name='Необходимо людей')

    class Meta:
        verbose_name = 'Активность'
        verbose_name_plural = 'Активности'

    def __str__(self):
        return self.name


class Person(models.Model):
    first_name = models.CharField(max_length=80, verbose_name='Имя')
    last_name = models.CharField(max_length=80, verbose_name='Фамилия')
    email = models.EmailField(verbose_name='email', null=True, blank=True)

    night_man = models.BooleanField(verbose_name='Ночной человек', null=False, default=False)
    arrival_datetime = models.DateTimeField(verbose_name='Дата и время прибытия', null=True, blank=True)
    departure_datetime = models.DateTimeField(verbose_name='Дата и время отъезда', null=True, blank=True)

    excluded_categories = models.ManyToManyField(Category, blank=True,
                                                 verbose_name='Категории, с которыми не готов работать')

    free_time_limit = models.DurationField(default=datetime.timedelta(hours=6),
                                           verbose_name='Лимит свободного времени')

    class Meta:
        verbose_name = 'Человек'
        verbose_name_plural = 'Человеки'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_schedule(self, event_pk, activity_type=None):
        if not activity_type:
            return ActivityOnEvent.objects.filter(event__pk=event_pk, person=self)
        return ActivityOnEvent.objects.filter(event__pk=event_pk, person=self,
                                              activity__category__activity_type__name=activity_type)

    def arrive_and_depart_filled(self):
        return all([self.arrival_datetime is not None, self.departure_datetime is not None])


class Event(models.Model):
    title = models.CharField(max_length=120, verbose_name='Название')
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')

    class Meta:
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'

    def __str__(self):
        return self.title

    def get_schedule(self, activity_type=None):
        if not activity_type:
            return ActivityOnEvent.objects.filter(event=self)
        return ActivityOnEvent.objects.filter(event=self, activity__category__activity_type__name=activity_type)


class ActivityOnEvent(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, verbose_name='Мероприятие')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, verbose_name='Активность')
    person = models.ManyToManyField(Person, blank=True, verbose_name='Кто занимается')

    start_dt = models.DateTimeField(verbose_name='Дата начала')
    end_dt = models.DateTimeField(verbose_name='Дата окончания')

    class Meta:
        verbose_name = 'Расписание активностей'
        verbose_name_plural = 'Расписание активностей'

    @admin.display(description='Продолжительность')
    def duration(self):
        if self.start_dt and self.end_dt:
            return self.end_dt - self.start_dt
        else:
            return None

    def __str__(self):
        return f'{self.activity.name} ({self.start_dt} - {self.end_dt})'
