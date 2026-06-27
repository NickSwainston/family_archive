from django.db.models.signals import post_save
from django.dispatch import receiver
from archive_app.models import FamilyMember


@receiver(post_save, sender=FamilyMember)
def update_partner(sender, instance, created, **kwargs):
    print(created)
    print(instance.partner)
    if created and instance.partner:
        partner = FamilyMember.objects.get(id=instance.partner.id)
        partner.partner = instance
        partner.save()
    if created and instance.partner2:
        partner2 = FamilyMember.objects.get(id=instance.partner2.id)
        partner2.partner2 = instance
        partner2.save()
