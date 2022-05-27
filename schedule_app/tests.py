import datetime

from django.test import TestCase

import schedule_app.constants as const
import schedule_app.models as models


class BaseModelTestCase(TestCase):
    def setUp(self):
        dt = datetime.date(2022, 1, 1)
        models.Event.objects.create(title="test_event", start_date=dt, end_date=dt)
        models.ActivityType.objects.create(name=const.OFFICIAL)
        models.ActivityType.objects.create(name=const.VOLUNTEER)
        models.ActivityType.objects.create(name=const.OTHER)
        models.Category.objects.create(name='official_category',
                                       activity_type=models.ActivityType.objects.get(name=const.OFFICIAL),
                                       time_coefficient=1.0,
                                       additional_time=datetime.time(minute=0))
        models.Category.objects.create(name='volunteer_category',
                                       activity_type=models.ActivityType.objects.get(name=const.VOLUNTEER),
                                       time_coefficient=2.0,
                                       additional_time=datetime.time(minute=10))
        models.Category.objects.create(name='other_category',
                                       activity_type=models.ActivityType.objects.get(name=const.OTHER),
                                       time_coefficient=2.0,
                                       additional_time=datetime.time(minute=10))

        models.Activity.objects.create(name='official_activity',
                                       category=models.Category.objects.get(name='official_category'))
        models.Activity.objects.create(name='volunteer_activity',
                                       category=models.Category.objects.get(name='volunteer_category'))
        models.Activity.objects.create(name='other_activity',
                                       category=models.Category.objects.get(name='other_category'))

        models.Person.objects.create(first_name='tester',
                                     last_name='testerson')


class ActivityOnEventTestCase(BaseModelTestCase):
    def setUp(self):
        super(ActivityOnEventTestCase, self).setUp()

        dt = datetime.date(2022, 1, 1)

        models.Person.objects.create(first_name='tester',
                                     last_name='testerson')

        m1 = models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                                   activity=models.Activity.objects.get(name='volunteer_activity'),
                                                   start_dt=datetime.datetime.combine(dt, datetime.time(12, 0, 0)),
                                                   end_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)))
        m1.person.add(models.Person.objects.get(pk=1))

        m2 = models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                                   activity=models.Activity.objects.get(name='volunteer_activity'),
                                                   start_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)),
                                                   end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))
        m2.person.add(models.Person.objects.get(pk=1))

        m3 = models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                                   activity=models.Activity.objects.get(name='volunteer_activity'),
                                                   start_dt=datetime.datetime.combine(dt, datetime.time(12, 5, 0)),
                                                   end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))
        m3.person.add(models.Person.objects.get(pk=1))

    def test_intersects(self):
        m1 = models.ActivityOnEvent.objects.get(pk=1)
        m2 = models.ActivityOnEvent.objects.get(pk=2)
        m3 = models.ActivityOnEvent.objects.get(pk=3)

        self.assertFalse(m1.is_intersects(m2))
        self.assertFalse(m2.is_intersects(m1))

        self.assertFalse(m1.is_intersects(m1))
        self.assertFalse(m2.is_intersects(m2))
        self.assertFalse(m3.is_intersects(m3))

        self.assertTrue(m1.is_intersects(m3))
        self.assertTrue(m3.is_intersects(m1))
        self.assertTrue(m2.is_intersects(m3))
        self.assertTrue(m3.is_intersects(m2))

    def test_duration(self):
        m1 = models.ActivityOnEvent.objects.get(pk=1)
        m2 = models.ActivityOnEvent.objects.get(pk=2)
        m3 = models.ActivityOnEvent.objects.get(pk=3)

        self.assertEqual(m1.duration(), datetime.timedelta(minutes=10))
        self.assertEqual(m2.duration(), datetime.timedelta(minutes=10))
        self.assertEqual(m3.duration(), datetime.timedelta(minutes=15))

    def test_duration_with_coef(self):
        m1 = models.ActivityOnEvent.objects.get(pk=1)
        m2 = models.ActivityOnEvent.objects.get(pk=2)
        m3 = models.ActivityOnEvent.objects.get(pk=3)

        self.assertEqual(m1.duration_with_coef(), datetime.timedelta(minutes=30))
        self.assertEqual(m2.duration_with_coef(), datetime.timedelta(minutes=30))
        self.assertEqual(m3.duration_with_coef(), datetime.timedelta(minutes=40))


class EventTestCase(BaseModelTestCase):
    def setUp(self):
        super(EventTestCase, self).setUp()
        dt = datetime.date(2022, 1, 1)
        models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                              activity=models.Activity.objects.get(name='official_activity'),
                                              start_dt=datetime.datetime.combine(dt, datetime.time(12, 0, 0)),
                                              end_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)))

        models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                              activity=models.Activity.objects.get(name='volunteer_activity'),
                                              start_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)),
                                              end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))

        models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                              activity=models.Activity.objects.get(name='other_activity'),
                                              start_dt=datetime.datetime.combine(dt, datetime.time(12, 5, 0)),
                                              end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))

    def test_get_schedule(self):
        event = models.Event.objects.get(title='test_event')
        self.assertEqual(len(event.get_schedule(const.OFFICIAL)), 1)
        self.assertEqual(len(event.get_schedule(const.VOLUNTEER)), 1)
        self.assertEqual(len(event.get_schedule(const.OTHER)), 1)
        self.assertEqual(len(event.get_schedule()), 3)


class PersonTestCase(BaseModelTestCase):
    def setUp(self):
        super(PersonTestCase, self).setUp()

        dt = datetime.date(2022, 1, 1)
        models.Person.objects.create(first_name='tester',
                                     last_name='second',
                                     arrival_datetime=datetime.datetime.combine(dt, datetime.time(12, 10, 0)),
                                     departure_datetime=datetime.datetime.combine(dt, datetime.time(13, 10, 0)))

        m1 = models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                                   activity=models.Activity.objects.get(name='volunteer_activity'),
                                                   start_dt=datetime.datetime.combine(dt, datetime.time(12, 0, 0)),
                                                   end_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)))
        m1.person.add(models.Person.objects.get(pk=1))

        m2 = models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                                   activity=models.Activity.objects.get(name='volunteer_activity'),
                                                   start_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)),
                                                   end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))
        m2.person.add(models.Person.objects.get(pk=1))

        m3 = models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                                   activity=models.Activity.objects.get(name='other_activity'),
                                                   start_dt=datetime.datetime.combine(dt, datetime.time(12, 5, 0)),
                                                   end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))
        m3.person.add(models.Person.objects.get(pk=1))

    def test_get_schedule(self):
        pk = models.Event.objects.get(title='test_event').pk

        p1 = models.Person.objects.get(first_name='tester', last_name='testerson')
        self.assertEqual(len(p1.get_schedule(pk, const.OFFICIAL)), 0)
        self.assertEqual(len(p1.get_schedule(pk, const.VOLUNTEER)), 2)
        self.assertEqual(len(p1.get_schedule(pk, const.OTHER)), 1)
        self.assertEqual(len(p1.get_schedule(pk)), 3)

    def test_arrive_and_depart_filled(self):
        p1 = models.Person.objects.get(first_name='tester', last_name='testerson')
        p2 = models.Person.objects.get(first_name='tester', last_name='second')

        self.assertFalse(p1.arrive_and_depart_filled())
        self.assertTrue(p2.arrive_and_depart_filled())


class ActivityTypeTestCase(BaseModelTestCase):
    def setUp(self):
        super(ActivityTypeTestCase, self).setUp()
        dt = datetime.date(2022, 1, 1)
        models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                              activity=models.Activity.objects.get(name='official_activity'),
                                              start_dt=datetime.datetime.combine(dt, datetime.time(12, 0, 0)),
                                              end_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)))

        models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                              activity=models.Activity.objects.get(name='volunteer_activity'),
                                              start_dt=datetime.datetime.combine(dt, datetime.time(12, 10, 0)),
                                              end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))

        models.ActivityOnEvent.objects.create(event=models.Event.objects.get(title='test_event'),
                                              activity=models.Activity.objects.get(name='other_activity'),
                                              start_dt=datetime.datetime.combine(dt, datetime.time(12, 5, 0)),
                                              end_dt=datetime.datetime.combine(dt, datetime.time(12, 20, 0)))

    def test_get_schedule(self):
        pk = models.Event.objects.get(title='test_event').pk
        for name in [const.OFFICIAL, const.VOLUNTEER, const.OTHER]:
            self.assertEqual(len(models.ActivityType.objects.get(name=name).get_schedule(pk)), 1)
