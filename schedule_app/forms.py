import datetime
from collections import namedtuple

from django.core.exceptions import ValidationError
from django.forms import ModelForm

from schedule_app import models


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
        fields = ('first_name', 'last_name', 'free_time_limit', 'night_man',
                  'arrival_datetime', 'departure_datetime', 'excluded_categories')


def check_excluded_categories(cleaned_data, person):
    if person.excluded_categories.filter(pk=cleaned_data.get('activity').category.pk):
        raise ValidationError({'person': f'{person.first_name} не изволит работать с этой категорией активностей.'})


def check_intersections(cleaned_data, person, existing_instance):
    Range = namedtuple('Range', ['start', 'end'])
    start_dt = cleaned_data.get('start_dt')
    end_dt = cleaned_data.get('end_dt')

    activities = models.ActivityOnEvent.objects.filter(event=cleaned_data.get('event'),
                                                       person=person)
    for act in activities:
        r1 = Range(start=start_dt, end=end_dt)
        r2 = Range(start=act.start_dt, end=act.end_dt)
        if r1.start > r2.end or r1.end < r2.start:
            break

        latest_start = max(r1.start, r2.start)
        earliest_end = min(r1.end, r2.end)
        delta = ((earliest_end - latest_start).seconds // 60) % 60 + 1

        overlap = max(0, delta)
        if overlap > 0 and existing_instance != act and existing_instance.pk != act.pk:
            act_detail = f'{act.activity.name} ({act.start_dt.strftime("%H:%M:%S")} - ' \
                         f'{act.end_dt.strftime("%H:%M:%S")})'
            raise ValidationError({
                'start_dt': f'Пересечение с другой активностью: {act_detail})',
                'end_dt': f'Пересечение с другой активностью: {act_detail})'
            })

    activities_sum = datetime.timedelta(0)
    activities_len = [act.end_dt - act.start_dt for act in activities]
    for act in activities_len:
        activities_sum += act

    if activities_sum > person.free_time_limit:
        raise ValidationError({'start_dt': 'Недостаточно свободного времени'})


class ActivityOnEventForm(ModelForm):
    class Meta:
        model = models.ActivityOnEvent
        fields = ('event', 'activity', 'person', 'start_dt', 'end_dt')

    def clean(self):
        super(ActivityOnEventForm, self).clean()
        persons = self.cleaned_data.get('person')
        for p in persons:
            check_excluded_categories(self.cleaned_data, p)
            check_intersections(self.cleaned_data, p, self.instance)

        return self.cleaned_data
