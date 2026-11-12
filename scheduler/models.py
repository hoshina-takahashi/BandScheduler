import uuid
from django.db import models
from django.contrib.auth.models import User


# ========== 個人カレンダー ==========

class PersonalSchedule(models.Model):
    """ログインユーザーの個人予定（マイカレンダー）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_schedules')
    date = models.DateField(verbose_name='日付')
    start_time = models.TimeField(verbose_name='開始時刻')
    end_time = models.TimeField(verbose_name='終了時刻')
    label = models.CharField(max_length=100, blank=True, verbose_name='予定名')

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f'{self.user.username} / {self.date} {self.start_time}〜{self.end_time} {self.label}'


class PersonalRecurringSchedule(models.Model):
    """ログインユーザーの定期予定（定期予定タブ）"""
    WEEKDAY_CHOICES = [
        (0, '月曜日'), (1, '火曜日'), (2, '水曜日'), (3, '木曜日'),
        (4, '金曜日'), (5, '土曜日'), (6, '日曜日'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_recurring_schedules')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, verbose_name='曜日')
    start_time = models.TimeField(verbose_name='開始時刻')
    end_time = models.TimeField(verbose_name='終了時刻')
    label = models.CharField(max_length=100, blank=True, verbose_name='予定名')

    class Meta:
        ordering = ['weekday', 'start_time']

    def __str__(self):
        return f'{self.user.username} / {self.get_weekday_display()} {self.start_time}〜{self.end_time}'


# ========== グループカレンダー ==========

class Room(models.Model):
    """グループ日程調整ルーム"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='グループ名')
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_rooms'
    )
    start_date = models.DateField(null=True, blank=True, verbose_name='募集期間開始')
    end_date = models.DateField(null=True, blank=True, verbose_name='募集期間終了')
    candidate_dates = models.JSONField(default=list, blank=True, verbose_name='候補日リスト')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    """ルームに参加したメンバー（ログインユーザーに紐づく）"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='room_memberships'
    )
    name = models.CharField(max_length=50, verbose_name='表示名')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('room', 'user')]

    def __str__(self):
        return f'{self.room.name} - {self.name}'


# ========== 旧モデル（後方互換のため残す）==========

class Schedule(models.Model):
    """旧：ルーム固有の予定（新UIでは PersonalSchedule を使用）"""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField(verbose_name='日付')
    start_time = models.TimeField(verbose_name='開始時刻')
    end_time = models.TimeField(verbose_name='終了時刻')
    label = models.CharField(max_length=100, blank=True, verbose_name='予定名')

    class Meta:
        ordering = ['date', 'start_time']


class RecurringSchedule(models.Model):
    """旧：ルーム固有の定期予定（新UIでは PersonalRecurringSchedule を使用）"""
    WEEKDAY_CHOICES = [
        (0, '月曜日'), (1, '火曜日'), (2, '水曜日'), (3, '木曜日'),
        (4, '金曜日'), (5, '土曜日'), (6, '日曜日'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='recurring_schedules')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, verbose_name='曜日')
    start_time = models.TimeField(verbose_name='開始時刻')
    end_time = models.TimeField(verbose_name='終了時刻')
    label = models.CharField(max_length=100, blank=True, verbose_name='予定名')

    class Meta:
        ordering = ['weekday', 'start_time']
