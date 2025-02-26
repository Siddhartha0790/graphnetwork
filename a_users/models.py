from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


from neomodel import StructuredNode, StringProperty, RelationshipTo, UniqueIdProperty

class Person(StructuredNode):

    name = StringProperty(unique_index=True, required=True)
    friends = RelationshipTo("Person", "FRIENDS_WITH")

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)
    displayname = models.CharField(max_length=20, null=True, blank=True)
    info = models.TextField(null=True, blank=True) 
    neo4j_profile_id = models.CharField(max_length=50, blank=True, null=True) 
    
    
    def save(self, *args, **kwargs):
        # Create a corresponding Neo4j node
        if not self.neo4j_profile_id:
            profile_node = Person(name=self.user.username).save()
            self.neo4j_profile_id = profile_node.element_id
        super().save(*args, **kwargs)
    def __str__(self):
        return str(self.user)
    
    @property
    def name(self):
        if self.displayname:
            return self.displayname
        return self.user.username 
    
    @property
    def avatar(self):
        if self.image:
            return self.image.url
        return f'{settings.STATIC_URL}images/avatar.svg'
