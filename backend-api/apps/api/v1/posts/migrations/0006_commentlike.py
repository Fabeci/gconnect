from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0005_alter_post_is_draft_alter_post_is_hidden_by_admin'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CommentLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='likes',
                    to='posts.comment',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='comment_likes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'indexes': [
                    models.Index(fields=['comment'], name='posts_comme_comment_idx'),
                ],
            },
        ),
        migrations.AlterUniqueTogether(
            name='commentlike',
            unique_together={('comment', 'user')},
        ),
    ]
