import 'package:flutter/material.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import '../widgets/comment_item_widget.dart';
import '../../domain/entities/comment.dart';

class CommentPage extends StatefulWidget {
  const CommentPage({super.key});

  @override
  State<CommentPage> createState() => _CommentPageState();
}

class _CommentPageState extends State<CommentPage> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _isReplying = false;

  void _showCommentField() {
    setState(() {
      _isReplying = true;
    });
    Future.delayed(const Duration(milliseconds: 100), () {
      FocusScope.of(context).requestFocus(_focusNode);
    });
  }

  final List<Comment> comments = [
    Comment(
      author: 'Amy collé Diaw',
      avatarUrl: 'assets/images/home/user1.png',
      message: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...',
      timeAgo: '2h',
      replies: [
        Comment(
          author: 'Moustapha sow',
          avatarUrl: 'assets/images/home/user2.png',
          message: 'Lorem ipsum dolor sit amet...',
          timeAgo: '30 min',
        ),
        Comment(
          author: 'Moustapha sow',
          avatarUrl: 'assets/images/home/user3.png',
          message: 'Lorem ipsum dolor sit amet...',
          timeAgo: '15 min',
        ),
      ],
    ),
    Comment(
      author: 'Amy collé Diaw',
      avatarUrl: 'assets/images/home/user4.png',
      message: 'Lorem ipsum dolor sit amet...',
      timeAgo: '3h',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        backgroundColor: Colors.white,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text('Retour', style: ThemeConstants.bodyStyle),
        elevation: 0,
      ),
      body: Stack(
        children: [
          ListView(
            padding: const EdgeInsets.all(16),
            physics: const BouncingScrollPhysics(),
            children: [
              // ✅ Résumé du post
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.asset('assets/images/posts/graduation_event.png'),
                  ),
                  const SizedBox(height: 8),
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.favorite, color: Colors.red),
                          SizedBox(width: 4),
                          Text('89'),
                        ],
                      ),
                      SizedBox(width: 24),
                      Text('24 Commentaires'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      const _PostAction(icon: Icons.favorite_border, label: 'J’aime'),
                      GestureDetector(
                        onTap: _showCommentField,
                        child: const _PostAction(icon: Icons.comment_outlined, label: 'Commenter'),
                      ),
                      const _PostAction(icon: Icons.share_outlined, label: 'Partager'),
                      const _PostAction(icon: Icons.send_outlined, label: 'Envoyer'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Divider(),
                ],
              ),

              // ✅ Commentaires
              ...comments.map((comment) => CommentItemWidget(comment: comment)).toList(),
              const SizedBox(height: 80), // espace pour le champ en bas
            ],
          ),

          // ✅ Champ de commentaire en bas
          if (_isReplying)
            Align(
              alignment: Alignment.bottomCenter,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                color: Colors.white,
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _controller,
                        focusNode: _focusNode,
                        decoration: const InputDecoration(
                          hintText: 'Écrire un commentaire...',
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.send, color: Colors.blue),
                      onPressed: () {
                        // À remplacer avec logique d'envoi
                        FocusScope.of(context).unfocus();
                        setState(() {
                          _isReplying = false;
                          _controller.clear();
                        });
                      },
                    )
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _PostAction extends StatelessWidget {
  final IconData icon;
  final String label;

  const _PostAction({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Colors.black54),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 13)),
      ],
    );
  }
}
