from django.test import Client
from django.db import connection
from django.urls import reverse

from test_app.models import BlogPost
from .main import BaseTestSetUp


class AuditHistoryAdminTest(BaseTestSetUp):

    def setUp(self):
        super(AuditHistoryAdminTest, self).setUp()
        self.c = Client()
        self.c.login(username=self.user_name, password=self.user_password)

    def test_add_new_instance(self):
        request = self.c.post(reverse(self.admin_add_url),
                              {
                                  'title': self.blog_title,
                                  'position': self.blog_position,
                              }, follow=True)
        self.assertEqual(200, request.status_code)
        qs = BlogPost.objects
        self.assertEqual(1, qs.count())
        self.assertEqual(self.blog_title, qs.first().title)
        self.assertEqual([], qs.first().history)

    def test_check_history_in_admin_after_save_with_audit_history(self):
        self.blog_post.save_with_audit_record(self.user, self.history_event, payload=self.payload)
        response = self.c.post(
            reverse(self.admin_change_url, args=[self.blog_post.id]),
            follow=True
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(self.payload['a'], str(response))
        self.assertIn(self.payload['b'], str(response))
        self.assertNotIn(self.payload_with_quotes['title'], str(response))

    def test_data_with_quotes(self):
        self.blog_post.save()
        with connection.cursor() as cursor:
            cursor.execute("""Update test_app_blogpost SET history = 
        '[{"actor": null, "email": "oreilly@southwestit.net",
         "event": "USER_CREATED_WITH_ACCOUNT",
          "timezone": "Etc/UTC",
           "csat_role": "admin",
            "last_name": "O''Reilly",
             "timestamp": "2017-12-15T14:12:33.039115+00:00",
              "first_name": "Mark",
               "csat_boards": [],
                "has_csat_access": true,
                 "is_account_admin": true,
                  "professional_title": "Service Manager"}]'
                   WHERE ID = %d""" % self.blog_post.id)
        response = self.c.post(
            reverse(self.admin_change_url, args=[self.blog_post.id]),
            self.payload_for_update,
            follow=True
        )
        self.assertEqual(200, response.status_code)
        qs = BlogPost.objects.get(pk=self.blog_post.id)
        self.assertEqual(self.payload_for_update['title'], qs.title)
        self.assertEqual(self.payload_for_update['position'], qs.position)
        self.assertEqual('O\'Reilly', qs.history[0]['last_name'])

    def test_another_data_with_quotes_in_history(self):
        self.blog_post.save_with_audit_record(None, self.history_event, payload=self.payload_with_quotes)
        response = self.c.post(
            reverse(self.admin_change_url, args=[self.blog_post.id]),
            self.payload_for_update,
            follow=True
        )
        self.assertEqual(200, response.status_code)
        qs = BlogPost.objects.get(pk=self.blog_post.id)
        self.assertEqual(self.payload_for_update['title'], qs.title)
        self.assertEqual(self.payload_for_update['position'], qs.position)
        self.assertEqual(self.payload_with_quotes['title'], qs.history[0]['payload']['title'])