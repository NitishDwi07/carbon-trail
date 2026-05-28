from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from ingestion.models import Organisation, UserProfile


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=400)

        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=400)

        token, _ = Token.objects.get_or_create(user=user)

        org = None
        try:
            org = user.profile.organisation
        except Exception:
            pass

        return Response({
            'token': token.key,
            'username': user.username,
            'org': org.name if org else None,
        })


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        org_name = request.data.get('org_name', 'Demo Corp')

        if not username or not password:
            return Response({'error': 'Username and password required'}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already taken'}, status=400)

        user = User.objects.create_user(username=username, password=password)

        org, _ = Organisation.objects.get_or_create(
            slug=org_name.lower().replace(' ', '-'),
            defaults={'name': org_name}
        )
        UserProfile.objects.create(user=user, organisation=org)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'username': username, 'org': org.name}, status=201)


class MeView(APIView):
    def get(self, request):
        org = None
        try:
            org = request.user.profile.organisation
        except Exception:
            pass
        return Response({
            'username': request.user.username,
            'org': org.name if org else None,
        })
