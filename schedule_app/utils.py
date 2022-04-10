import datetime
from collections import namedtuple

from django.shortcuts import reverse


def need_peoples_transform(value):
    """
    Функция проверяет, набрано ли необходимое количество людей.
    Формирует ссылку на админку, если нет
    """
    need = value['need_peoples']
    current = value['num_peoples']
    msg = f'{current}/{need}'

    if need == current:
        return f'Заполнено ({msg})'
    diff = need - current
    admin_url = reverse('admin:schedule_app_activityonevent_change', args=(value['activity_pk'],))

    return f'<a href="{admin_url}" target="_blank">Требуется еще {diff} ({msg})</a>'


def date_transform(value):
    """
    Формирование строки с временем начала и конца активности,
    продолжительности и продолжительности с учетом коэффициента
    """
    start = value['start_dt']
    end = value['end_dt']
    coef = value['time_coef']
    at = value['additional_time']

    dt = datetime.timedelta(hours=at.hour, minutes=at.minute, seconds=at.second)

    duration = int((end - start).total_seconds()) // 60
    duration_with_coef = int(duration * coef) + int(dt.total_seconds()) // 60

    duration = human_readable_time(duration)
    duration_with_coef = human_readable_time(duration_with_coef)
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
