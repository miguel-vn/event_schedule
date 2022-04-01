import pandas as pd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, path, reverse
from django.views.generic import ListView

from schedule_app.models import Event, ActivityOnEvent


class EventsList(ListView):
    model = Event
    paginate_by = 10
    template_name = 'events.html'

    def get_queryset(self):
        if isinstance(self.request.user, AnonymousUser):
            return []
        events = Event.objects.all().order_by('-start_date', '-end_date')

        return events


def login(_):
    return redirect('/admin')


class BaseOperations(LoginRequiredMixin):
    login_url = reverse_lazy('login')


def show_schedule(request, pk):
    objs = ActivityOnEvent.objects.filter(event__pk=pk).order_by('start_dt', 'end_dt')
    data = []
    activity_pk = {}
    for activity in objs:
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'duration': (activity.end_dt - activity.start_dt).seconds // 60,
                    'activity': activity.activity.name,
                    'persons': [f"{person.first_name} {person.last_name}" for person in activity.person.all()],
                    'need_peoples': activity.activity.need_peoples}

        activity_pk[activity.activity.name] = activity.pk

        data.append(row_data)

    df = pd.DataFrame(data)

    df['num_peoples'] = df['persons'].apply(len)

    def need_peoples_transform(value):
        need = value['need_peoples']
        current = value['num_peoples']
        msg = f'{current}/{need}'

        if need == current:
            return f'Заполнено ({msg})'
        diff = need - current
        return f'Требуется еще {diff} ({msg})'

    def date_transform(value):
        start = value['start_dt']
        end = value['end_dt']
        duration = (end - start).seconds // 60
        if duration > 60:
            h = duration // 60
            m = duration % 60
            duration = f"{h} ч. {m} мин."
        else:
            duration = f"{duration} мин."

        return f"{start.strftime('%d.%m %H:%M')} - {end.strftime('%H:%M')} ({duration})"

    def highlight(s):
        return "background: #00FF00" if s == 'Участвует' else None

    df['need_peoples'] = df[['need_peoples', 'num_peoples']].apply(need_peoples_transform, axis=1)
    df['start_dt'] = df[['start_dt', 'end_dt']].apply(date_transform, axis=1)

    df.drop(columns=['num_peoples'], inplace=True)
    df = df.explode('persons').reset_index(drop=True)
    df['values'] = 1
    df = df.pivot_table(values='values', index='persons', columns=['activity', 'start_dt', 'need_peoples'],
                        fill_value=0).astype('int8')
    df = df.applymap(lambda elem: 'Участвует' if elem == 1 else 'Доступен')

    table_styles = [{'selector': 'th.col_heading', 'props': 'text-align: center;'},
                    {'selector': 'th.col_heading.level0', 'props': 'font-size: 1.5em;'}]

    for i, col in enumerate(df.columns):
        if 'Требуется еще' in col[2]:
            # admin_url = reverse('admin:schedule_app_activityonevent_change', args=(1,))
            table_styles.append({'selector': f'th.col_heading.level2.col{i}', 'props': 'background: #FFD700;'})

    df.columns.set_names(['Активность', 'Время', 'Наполнение'], inplace=True)
    df.index.set_names([''], inplace=True)
    df = df.style.applymap(highlight)

    out = df.set_table_attributes('class="table"').set_table_styles(table_styles, overwrite=False).to_html()

    return render(request, '../templates/event_detail.html',
                  {'table_content': out,
                   'event': Event.objects.get(pk=pk)})
