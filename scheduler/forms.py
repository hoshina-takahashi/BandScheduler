# scheduler/forms.py
from django import forms
from .models import Room, Member


class RoomCreateForm(forms.ModelForm):
    """ルーム作成フォーム"""
    class Meta:
        model = Room
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': '例：〇〇大学とのライブ企画',
                'autofocus': True,
            })
        }
        labels = {
            'name': 'ルーム名',
        }


class MemberJoinForm(forms.Form):
    """メンバー参加フォーム（Modelに直接紐付けない）"""
    name = forms.CharField(
        max_length=50,
        label='あなたの名前',
        widget=forms.TextInput(attrs={
            'placeholder': '例：山田太郎',
            'autofocus': True,
        })
    )