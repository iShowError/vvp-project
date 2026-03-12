from rest_framework import serializers
from logs.models import Issue, Comment, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'username', 'role']


class CommentSerializer(serializers.ModelSerializer):
    engineer_email = serializers.EmailField(source='engineer.email', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'text', 'engineer_email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'engineer_email', 'created_at', 'updated_at']


class IssueListSerializer(serializers.ModelSerializer):
    dept_head_email = serializers.EmailField(source='dept_head.email', read_only=True)
    comments_count = serializers.IntegerField(source='get_comments_count', read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'device_type', 'description', 'status', 'priority',
            'created_at', 'updated_at', 'dept_head_email', 'comments_count',
        ]
        read_only_fields = fields


class IssueDetailSerializer(serializers.ModelSerializer):
    dept_head_email = serializers.EmailField(source='dept_head.email', read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'device_type', 'description', 'status', 'priority',
            'created_at', 'updated_at', 'dept_head_email', 'comments',
            'first_response_at', 'resolved_at',
            'sla_response_deadline', 'sla_resolution_deadline',
            'sla_response_breached', 'sla_resolution_breached',
        ]
        read_only_fields = fields


class IssueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = ['device_type', 'description', 'priority']


class IssueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = ['status', 'priority']

    def validate(self, attrs):
        if self.instance and self.instance.status in ('closed', 'completed'):
            raise serializers.ValidationError('Cannot update a closed or completed issue.')
        return attrs
