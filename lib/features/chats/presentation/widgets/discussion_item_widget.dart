import 'package:flutter/material.dart';

class DiscussionItemWidget extends StatelessWidget {
  final String name;
  final String subtitle;
  final String date;
  final String imagePath;
  final bool isOnline;
  final int unreadCount;

  const DiscussionItemWidget({
    super.key,
    required this.name,
    required this.subtitle,
    required this.date,
    required this.imagePath,
    this.isOnline = false,
    this.unreadCount = 0,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Stack(
        children: [
          CircleAvatar(
            backgroundImage: AssetImage(imagePath),
            radius: 24,
          ),
          if (isOnline)
            const Positioned(
              bottom: 0,
              right: 0,
              child: CircleAvatar(
                backgroundColor: Colors.white,
                radius: 6,
                child: CircleAvatar(
                  radius: 4,
                  backgroundColor: Colors.green,
                ),
              ),
            ),
        ],
      ),
      title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
      subtitle: Text(subtitle, overflow: TextOverflow.ellipsis),
      trailing: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(date, style: const TextStyle(fontSize: 12)),
          if (unreadCount > 0)
            Container(
              margin: const EdgeInsets.only(top: 4),
              padding: const EdgeInsets.all(6),
              decoration: const BoxDecoration(
                color: Colors.blue,
                shape: BoxShape.circle,
              ),
              child: Text(
                '$unreadCount',
                style: const TextStyle(color: Colors.white, fontSize: 10),
              ),
            ),
        ],
      ),
    );
  }
}
