from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import User, Warehouse, Product, Movement, AuditLog

@receiver(post_save, sender=User)
@receiver(post_save, sender=Warehouse)
@receiver(post_save, sender=Product)
@receiver(post_save, sender=Movement)
def log_save(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    AuditLog.objects.create(
        user=instance.performed_by if sender == Movement else None,
        action=action,
        model=sender.__name__,
        object_id=instance.id,
        details=str(instance)
    )

@receiver(post_delete, sender=User)
@receiver(post_delete, sender=Warehouse)
@receiver(post_delete, sender=Product)
@receiver(post_delete, sender=Movement)
def log_delete(sender, instance, **kwargs):
    AuditLog.objects.create(
        user=None,
        action='deleted',
        model=sender.__name__,
        object_id=instance.id,
        details=str(instance)
    )