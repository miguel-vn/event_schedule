import datetime as dt

from django.core.exceptions import ValidationError
from django.forms import ModelForm

import schedule_app.constants as const
from schedule_app import models


class CategoryForm(ModelForm):
    class Meta:
        model = models.Category
        fields = ('name', 'activity_type', 'work_with_peoples', 'time_coefficient', 'additional_time')


class ActivityTypeForm(ModelForm):
    class Meta:
        model = models.ActivityType
        fields = ('name',)


class ActivityForm(ModelForm):
    class Meta:
        model = models.Activity
        fields = ('category', 'name', 'description', 'need_peoples')


class EventForm(ModelForm):
    class Meta:
        model = models.Event
        fields = ('title', 'start_date', 'end_date')


class PersonForm(ModelForm):
    class Meta:
        model = models.Person
        fields = ('first_name', 'last_name', 'email', 'free_time_limit', 'night_man',
                  'arrival_datetime', 'departure_datetime', 'excluded_categories')


def check_excluded_categories(cleaned_data, person):
    if person.excluded_categories.filter(pk=cleaned_data.get('activity').category.pk):
        raise ValidationError({'person': f'{person.first_name} не изволит работать с этой категорией активностей.'})


def check_person_incoming_dates(cleaned_data, person):
    full_name = f'{person.first_name} {person.last_name}'

    activity_start_dt = cleaned_data.get('activity').start_dt
    activity_end_dt = cleaned_data.get('activity').end_dt

    if person.arrival_datetime is None or person.departure_datetime is None:
        raise ValidationError({'start_dt': f'У {full_name} не заполнено время приезда и отъезда',
                               'end_dt': f'У {full_name} не заполнено время приезда и отъезда'})

    checks = [person.arrival_datetime <= activity_start_dt <= person.departure_datetime,
              person.arrival_datetime <= activity_end_dt <= person.departure_datetime]
    if not all(checks):
        event_title = cleaned_data.get('event').title
        raise ValidationError({
            'start_dt': f'{full_name} не будет на {event_title} в это время',
            'end_dt': f'{full_name} не будет на {event_title} в это время'
        })


def check_intersections(cleaned_data, person, existing_instance):
    activities = person.get_schedule(cleaned_data.get('event').pk)

    for act in activities:
        if existing_instance.is_intersects(act):
            act_detail = f'{act.activity.name} ({act.start_dt.strftime("%H:%M:%S")} - ' \
                         f'{act.end_dt.strftime("%H:%M:%S")})'
            raise ValidationError({
                'start_dt': f'Пересечение с другой активностью: {act_detail})',
                'end_dt': f'Пересечение с другой активностью: {act_detail})'
            })


def check_free_time_limit(cleaned_data, person):
    start_dt = cleaned_data.get('start_dt')
    end_dt = cleaned_data.get('end_dt')
    activities = person.get_schedule(cleaned_data.get('event').pk, const.VOLUNTEER)

    new = models.ActivityOnEvent(event=cleaned_data.get('event'),
                                 activity=cleaned_data.get('activity'),
                                 start_dt=start_dt,
                                 end_dt=end_dt)
    activities_sum = new.duration_with_coef()

    for act in activities:
        activities_sum += act.duration_with_coef()

    if activities_sum > person.free_time_limit:
        raise ValidationError({'start_dt': 'Недостаточно свободного времени'})


class ActivityOnEventForm(ModelForm):
    class Meta:
        model = models.ActivityOnEvent
        fields = ('event', 'activity', 'person', 'start_dt', 'end_dt')

    def __init__(self, *args, **kwargs):
        super(ActivityOnEventForm, self).__init__(*args, **kwargs)
        latest_event = models.Event.objects.latest('start_date')
        self.fields['event'].initial = latest_event
        self.fields['start_dt'].initial = dt.datetime.combine(models.Event.objects.latest('start_date').start_date,
                                                              dt.time(9, 0, 0))
        self.fields['end_dt'].initial = dt.datetime.combine(models.Event.objects.latest('start_date').start_date,
                                                            dt.time(10, 0, 0))

    def clean(self):
        super(ActivityOnEventForm, self).clean()
        persons = self.cleaned_data.get('person')
        for p in persons:
            check_excluded_categories(self.cleaned_data, p)
            if self.cleaned_data.get('activity').category.activity_type.name == const.VOLUNTEER:
                check_free_time_limit(self.cleaned_data, p)
            check_intersections(self.cleaned_data, p, self.instance)

        return self.cleaned_data
