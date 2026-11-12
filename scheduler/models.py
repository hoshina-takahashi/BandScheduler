# scheduler/models.py
import uuid
from django.db import models


class Room(models.Model):
    """
    日程調整ルーム。URLで共有する単位。
    例：「〇〇大学とのライブ企画」ごとに1つ作る
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='ルーム名')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    """
    ルームに参加したメンバー1人。
    ログイン不要で名前だけ入れて参加できる設計。
    """
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='members')
    name = models.CharField(max_length=50, verbose_name='名前')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.room.name} - {self.name}'


class Schedule(models.Model):
    """
    メンバーが「埋まっている」時間帯。
    空き時間ではなく埋まり時間を保存するのがポイント。
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField(verbose_name='日付')
    start_time = models.TimeField(verbose_name='開始時刻')
    end_time = models.TimeField(verbose_name='終了時刻')
    label = models.CharField(max_length=100, blank=True, verbose_name='予定名')

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f'{self.member.name} / {self.date} {self.start_time}〜{self.end_time}'
    

class RecurringSchedule(models.Model):
    """
    定期予定。毎週◯曜◯時〜◯時という繰り返しルール。
    表示するとき、対象週の日付に展開して使う。
    """
    WEEKDAY_CHOICES = [
        (0, '月曜日'),
        (1, '火曜日'),
        (2, '水曜日'),
        (3, '木曜日'),
        (4, '金曜日'),
        (5, '土曜日'),
        (6, '日曜日'),
    ]

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='recurring_schedules'
    )
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, verbose_name='曜日')
    start_time = models.TimeField(verbose_name='開始時刻')
    end_time = models.TimeField(verbose_name='終了時刻')
    label = models.CharField(max_length=100, blank=True, verbose_name='予定名')

    class Meta:
        ordering = ['weekday', 'start_time']

    def __str__(self):
        return f'{self.member.name} / {self.get_weekday_display()} {self.start_time}〜{self.end_time}'    