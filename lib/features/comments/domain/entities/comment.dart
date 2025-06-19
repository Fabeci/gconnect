class Comment {
  final String author;
  final String avatarUrl;
  final String message;
  final String timeAgo;
  final List<Comment> replies;

  Comment({
    required this.author,
    required this.avatarUrl,
    required this.message,
    required this.timeAgo,
    this.replies = const [],
  });
}
