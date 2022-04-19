import datetime
from collections import namedtuple

import pandas as pd
from django.shortcuts import reverse


def need_peoples_transform(value):
    """
    Функция проверяет, набрано ли необходимое количество людей.
    Формирует ссылку на админку, если нет
    """
    need = value['need_peoples']
    current = value['num_peoples']
    msg = f'{current}/{need}'
    admin_url = reverse('admin:schedule_app_activityonevent_change', args=(value['activity_pk'],))

    if need == current:
        return f'<a href="{admin_url}" target="_blank">Заполнено ({msg})</a>'

    diff = need - current

    return f'<a href="{admin_url}" target="_blank">Требуется еще {diff} ({msg})</a>'


def create_url_for_person(event, person):
    person_url = reverse('person', args=(event.pk, person.pk))
    return f'<a href="{person_url}" target="_blank">{person.last_name} {person.first_name}</a>'


def get_duration(value):
    start = value['start_dt']
    end = value['end_dt']
    return int((end - start).total_seconds())


def get_duration_with_coef(value):
    duration = value['duration']
    coef = float(value['time_coef'])
    at = value['additional_time']
    dt = datetime.timedelta(hours=at.hour, minutes=at.minute, seconds=at.second).total_seconds()

    return int(coef * duration) + int(dt)


def total_person_load(value):
    duration_with_coef = human_readable_time(value // 60)
    return str(duration_with_coef)


def date_transform(value):
    """
    Формирование строки с временем начала и конца активности,
    продолжительности и продолжительности с учетом коэффициента
    """
    start = value['start_dt']
    end = value['end_dt']
    duration = human_readable_time(value['duration'] // 60)
    duration_with_coef = human_readable_time(value['duration_with_coef'] // 60)

    return f"{start.strftime('%d.%m %H:%M')} - {end.strftime('%H:%M')} ({duration} - {duration_with_coef})"


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


def replace_person_status(value):
    if value == 1:
        return 'Участвует'
    elif value == -1:
        return 'Недоступен'
    return 'Доступен'


def highlight(s):
    """
    Возвращает CSS-свойство для заливки фона, в зависимости от содержимого ячейки
    """
    if s == 'Участвует':
        return "background: #00FA9A"
    elif s == 'Недоступен':
        return "background: #FA8072"
    return None


def is_intersects(start_dt, end_dt, activity, checked_activity):
    Range = namedtuple('Range', ['start', 'end'])

    r1 = Range(start=start_dt, end=end_dt)
    r2 = Range(start=activity.start_dt, end=activity.end_dt)
    if r1.start > r2.end or r1.end < r2.start:
        return False

    latest_start = max(r1.start, r2.start)
    earliest_end = min(r1.end, r2.end)
    delta = ((earliest_end - latest_start).seconds // 60) % 60 + 1

    overlap = max(0, delta)
    if overlap > 0 and checked_activity != activity and checked_activity.pk != activity.pk:
        return True
    return False


class Act:
    def __init__(self, start_dt, end_dt, pk: int):
        self.pk = pk
        self.start_dt = start_dt
        self.end_dt = end_dt


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
