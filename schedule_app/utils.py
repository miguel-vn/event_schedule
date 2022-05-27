import pandas as pd
from django.shortcuts import reverse

from schedule_app.models import Event

dt_format = '%d.%m %H:%M'


class ScheduleResponse:
    empty_schedule_message = '<div class="container"><h2>Расписание отсутствует</h2></div>'

    def __init__(self, current_page_name, event_pk, content=None):
        self.current_page_name = current_page_name
        self.event = Event.objects.get(pk=event_pk)
        self.__content = content

    @property
    def content(self):
        return self.__content if self.__content else self.empty_schedule_message

    @content.setter
    def content(self, value):
        self.__content = value

    def as_dict(self):
        return {'table_content': self.content,
                'current_page': self.current_page_name,
                'event': self.event}


def need_peoples_transform(value):
    """
    Функция проверяет, набрано ли необходимое количество людей.
    Формирует ссылку на админку, если нет
    """
    need = value['need_peoples']
    current = len(value['persons'])
    msg = f'{current}/{need}'
    admin_url = reverse('admin:schedule_app_activityonevent_change', args=(value['activity_pk'],))

    if need == current:
        return f'<a href="{admin_url}" target="_blank">Заполнено ({msg})</a>'

    diff = need - current

    return f'<a href="{admin_url}" target="_blank">Требуется еще {diff} ({msg})</a>'


def create_url_for_person(event, person):
    person_url = reverse('person', args=(event.pk, person.pk))
    return f'<a href="{person_url}">{person.last_name} {person.first_name}</a>'


def date_transform(value, duration, duration_with_coef):
    """
    Формирование строки с временем начала и конца активности,
    продолжительности и продолжительности с учетом коэффициента
    """
    start = value['start_dt']
    end = value['end_dt']
    duration = human_readable_time(int(duration.total_seconds()) // 60)
    duration_with_coef = human_readable_time(int(duration_with_coef.total_seconds()) // 60)

    return f"{start.strftime(dt_format)} - {end.strftime('%H:%M')} ({duration} - {duration_with_coef})"


def human_readable_time(value):
    """
    Перевод времени в человекочитаемый формат
    """
    if value > 60:
        h = value // 60
        m = value % 60
        value = f"{h} ч. {m} мин."
    else:
        value = f"{value} мин."
    return value


def create_google_calendar_format_schedule(activities):
    date_format = '%Y-%m-%d'
    time_format = '%H:%M:%S'
    data = []
    for activity in activities:
        data.append({'Subject': activity.activity.name,
                     'Start Date': activity.start_dt.strftime(date_format),
                     'Start Time': activity.start_dt.strftime(time_format),
                     'End Date': activity.end_dt.strftime(date_format),
                     'End Time': activity.end_dt.strftime(time_format),
                     'Description': activity.activity.description})

    return pd.DataFrame(data, dtype=str)
