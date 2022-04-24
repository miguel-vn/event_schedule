from django.core.exceptions import ValidationError
from django.forms import ModelForm

from schedule_app import models
from schedule_app.utils import is_intersects, get_duration_with_coef


class CategoryForm(ModelForm):
    class Meta:
        model = models.Category
        fields = ('name', 'work_with_peoples', 'time_coefficient', 'additional_time')


class ActivityTypeForm(ModelForm):
    class Meta:
        model = models.ActivityType
        fields = ('name',)


class ActivityForm(ModelForm):
    class Meta:
        model = models.Activity
        fields = ('category', 'activity_type', 'name', 'description', 'need_peoples')


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
    activity_start_dt = cleaned_data.get('activity').start_dt
    activity_end_dt = cleaned_data.get('activity').end_dt

    checks = [person.arrival_datetime <= activity_start_dt <= person.departure_datetime,
              person.arrival_datetime <= activity_end_dt <= person.departure_datetime]
    if not all(checks):
        event_title = cleaned_data.get('event').title
        full_name = f'{person.first_name} {person.last_name}'
        raise ValidationError({
            'start_dt': f'{full_name} не будет на {event_title} в это время',
            'end_dt': f'{full_name} не будет на {event_title} в это время'
        })


def check_intersections(cleaned_data, person, existing_instance):
    start_dt = cleaned_data.get('start_dt')
    end_dt = cleaned_data.get('end_dt')

    activities = models.ActivityOnEvent.objects.filter(event=cleaned_data.get('event'),
                                                       person=person)
    for act in activities:
        if is_intersects(start_dt, end_dt, act, existing_instance):
            act_detail = f'{act.activity.name} ({act.start_dt.strftime("%H:%M:%S")} - ' \
                         f'{act.end_dt.strftime("%H:%M:%S")})'
            raise ValidationError({
                'start_dt': f'Пересечение с другой активностью: {act_detail})',
                'end_dt': f'Пересечение с другой активностью: {act_detail})'
            })

    time_params = {'duration': int((end_dt - start_dt).total_seconds()),
                   'time_coef': float(cleaned_data.get('activity').category.time_coefficient),
                   'additional_time': cleaned_data.get('activity').category.additional_time}

    activities_sum = get_duration_with_coef(time_params)

    for act in activities.filter(activity__activity_type__name='volunteer_schedule'):
        time_params = {'duration': int((act.end_dt - act.start_dt).total_seconds()),
                       'time_coef': float(act.activity.category.time_coefficient),
                       'additional_time': act.activity.category.additional_time}

        activities_sum += get_duration_with_coef(time_params)

    if activities_sum > person.free_time_limit.total_seconds():
        raise ValidationError({'start_dt': 'Недостаточно свободного времени'})


class ActivityOnEventForm(ModelForm):
    class Meta:
        model = models.ActivityOnEvent
        fields = ('event', 'activity', 'person', 'start_dt', 'end_dt')

    def __init__(self, *args, **kwargs):
        super(ActivityOnEventForm, self).__init__(*args, **kwargs)
        self.fields['event'].initial = models.Event.objects.latest('start_date')

    def clean(self):
        super(ActivityOnEventForm, self).clean()
        persons = self.cleaned_data.get('person')
        for p in persons:
            check_excluded_categories(self.cleaned_data, p)
            check_intersections(self.cleaned_data, p, self.instance)

        return self.cleaned_data
