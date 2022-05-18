import schedule_app.constants as const
import schedule_app.models as models


def get_full_schedule(event_pk):
    return __get_schedule(event_pk)


def get_official_schedule(event_pk):
    return __get_schedule(event_pk, const.OFFICIAL)


def get_volunteer_schedule(event_pk):
    return __get_schedule(event_pk, const.VOLUNTEER)


def get_other_schedule(event_pk):
    return __get_schedule(event_pk, const.OTHER)


def __get_schedule(event_pk, activity_type: str = None):
    return models.Event.objects.get(pk=event_pk).get_schedule(activity_type)
