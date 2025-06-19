import 'package:flutter/material.dart';
import '../../domain/entities/comment.dart';

class CommentItemWidget extends StatelessWidget {
  final Comment comment;
  final bool isReply;

  const CommentItemWidget({
    super.key,
    required this.comment,
    this.isReply = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(left: isReply ? 40 : 0, bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(backgroundImage: AssetImage(comment.avatarUrl), radius: 16),
              const SizedBox(width: 8),
              Text(
                comment.author,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(width: 8),
              Text(comment.timeAgo, style: const TextStyle(color: Colors.grey)),
            ],
          ),
          const SizedBox(height: 8),
          Text(comment.message),
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(Icons.favorite_border, size: 16, color: Colors.grey[700]),
              const SizedBox(width: 4),
              const Text('J’aime', style: TextStyle(fontSize: 12)),
              const SizedBox(width: 16),
              Icon(Icons.reply_outlined, size: 16, color: Colors.grey[700]),
              const SizedBox(width: 4),
              const Text('Réponses', style: TextStyle(fontSize: 12)),
              const Spacer(),
              Icon(Icons.more_horiz, size: 18),
            ],
          ),
          ...comment.replies.map(
            (reply) => CommentItemWidget(comment: reply, isReply: true),
          ),
        ],
      ),
    );
  }
}
