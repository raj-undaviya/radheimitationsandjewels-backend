# policies/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from .models import Policy, PolicyAudit
from .serializers import PolicySerializer, PolicyAuditSerializer
from users.permissions import IsAdminUserRole


def calculate_compliance_score(policies):
    """
    Score logic:
    - Each policy that exists:         +20 points (max 5 core policies = 100)
    - Each outdated policy (6+ months): -15 points
    - Each inactive policy:            -10 points
    """
    if not policies.exists():
        return 0

    core_policies = [
        'terms_and_conditions',
        'shipping_policy',
        'refund_and_return',
        'privacy_policy',
    ]

    score = 0
    for policy_type in core_policies:
        policy = policies.filter(policy_type=policy_type).first()
        if policy:
            score += 25                     # exists
            if policy.is_outdated:
                score -= 15                 # outdated
            if not policy.is_active:
                score -= 10                 # inactive

    return max(0, min(score, 100))          # clamp between 0 and 100


# ─── Admin: List + Create Policies ───────────────────────────────────────────
class AdminPolicyView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), IsAdminUserRole()]
        return [IsAuthenticated(), IsAdminUserRole()]

    def get(self, request):
        policies = Policy.objects.all().order_by('-updated_at')

        # ✅ Stats
        total_policies   = policies.count()
        compliance_score = calculate_compliance_score(policies)

        # ✅ Audit info
        audit = PolicyAudit.objects.order_by('-created_at').first()

        serializer = PolicySerializer(policies, many=True)

        return Response(
            {
                "message":  "Policies retrieved successfully",
                "stats": {
                    "total_policies":   total_policies,
                    "compliance_score": compliance_score,
                    "next_audit_date":  audit.next_audit_date if audit else None,
                },
                "data": serializer.data,
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = PolicySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Policy created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"message": "Policy creation failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


# ─── Admin: Get + Update + Delete Single Policy ───────────────────────────────
class AdminPolicyDetailView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get_object(self, policy_id):
        try:
            return Policy.objects.get(id=policy_id)
        except Policy.DoesNotExist:
            return None

    def get(self, request, policy_id):
        policy = self.get_object(policy_id)
        if not policy:
            return Response(
                {"message": "Policy not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {"message": "Policy details", "data": PolicySerializer(policy).data},
            status=status.HTTP_200_OK
        )

    def put(self, request, policy_id):
        policy = self.get_object(policy_id)
        if not policy:
            return Response(
                {"message": "Policy not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PolicySerializer(policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Policy updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"message": "Update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, policy_id):
        policy = self.get_object(policy_id)
        if not policy:
            return Response(
                {"message": "Policy not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        policy.delete()
        return Response(
            {"message": "Policy deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


# ─── Public: Get Policy by Type (for frontend customers) ─────────────────────
class PublicPolicyView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, policy_type):
        try:
            policy     = Policy.objects.get(policy_type=policy_type, is_active=True)
            serializer = PolicySerializer(policy)
            return Response(
                {"message": "Policy retrieved", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        except Policy.DoesNotExist:
            return Response(
                {"message": "Policy not found"},
                status=status.HTTP_404_NOT_FOUND
            )


# ─── Admin: Audit Management ──────────────────────────────────────────────────
class AdminPolicyAuditView(APIView):

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        audit = PolicyAudit.objects.order_by('-created_at').first()
        if not audit:
            return Response(
                {"message": "No audit scheduled yet"},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {"message": "Audit details", "data": PolicyAuditSerializer(audit).data},
            status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = PolicyAuditSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Audit scheduled successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"message": "Failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def put(self, request):
        audit = PolicyAudit.objects.order_by('-created_at').first()
        if not audit:
            return Response(
                {"message": "No audit found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PolicyAuditSerializer(audit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Audit updated", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"message": "Update failed", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
class UserPolicyView(APIView):

    def get(self, request):
        try:
            print(request.user)
            policies = Policy.objects.all().order_by('-updated_at')
            serializer = PolicySerializer(policies, many=True)
            return Response(
                {"message": "Active policies retrieved", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"message": "Failed to retrieve policies"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserPolicyDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, policy_type):
        print(f"User {request.user} requested policy of type: {policy_type}")
        try:
            policy     = Policy.objects.get(policy_type=policy_type, is_active=True)
            serializer = PolicySerializer(policy)
            return Response(
                {"message": "Policy retrieved", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        except Policy.DoesNotExist:
            return Response(
                {"message": "Policy not found"},
                status=status.HTTP_404_NOT_FOUND
            )