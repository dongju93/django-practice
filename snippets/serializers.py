from rest_framework import serializers

from snippets.models import Snippet  # LANGUAGE_CHOICES, STYLE_CHOICES

# class SnippetSerializer(serializers.Serializer):
#     """검증 플래그 (required, max_length, default)를 지닌 직렬화 클래스"""
#
#     id = serializers.IntegerField(read_only=True)
#     title = serializers.CharField(required=False, allow_blank=True, max_length=100)
#     # HTML로 렌더링될 때 <textarea> 위젯을 사용하도록 지정
#     code = serializers.CharField(style={"base_template": "textarea.html"})
#     linenos = serializers.BooleanField(required=False)
#     language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, default="python")
#     style = serializers.ChoiceField(choices=STYLE_CHOICES, default="friendly")
#
#     def create(self, validated_data):
#         """
#         새 인스턴스 생성 시, 유효성 검사를 통과한 데이터(validated_data)를 사용하여
#         새 Snippet 인스턴스를 생성하고 반환합니다
#         """
#         return Snippet.objects.create(**validated_data)
#
#     def update(self, instance, validated_data):
#         """
#         기존 인스턴스 업데이트 시, 기존 인스턴스와 유효성 검사를 통과한 데이터(validated_data)를 사용하여
#         인스턴스를 업데이트하고 반환
#         """
#         # foo.get("bar", instance.bar) 패턴은 요청 데이터에 해당 필드가 없으면 기존 값을 유지
#         instance.title = validated_data.get("title", instance.title)
#         instance.code = validated_data.get("code", instance.code)
#         instance.linenos = validated_data.get("linenos", instance.linenos)
#         instance.language = validated_data.get("language", instance.language)
#         instance.style = validated_data.get("style", instance.style)
#         instance.save()
#         return instance


class SnippetSerializer(serializers.ModelSerializer):
    """ModelSerializer는 자동으로 필드를 결정하고, create() 및 update() 메서드의 간단한 기본 구현을 제공"""

    class Meta:
        # 사용할 모델을 지정
        model = Snippet
        # API에 포함될 필드 목록을 명시적으로 지정
        fields = ["id", "title", "code", "linenos", "language", "style"]
