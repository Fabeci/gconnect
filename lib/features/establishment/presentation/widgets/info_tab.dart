import 'package:flutter/material.dart';

class InfoTab extends StatelessWidget {
  const InfoTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: const [
        Row(
          children: [
            Icon(Icons.location_on),
            SizedBox(width: 8),
            Text('Dakar, Sénégal'),
          ],
        ),
        SizedBox(height: 8),
        Row(
          children: [
            Icon(Icons.school),
            SizedBox(width: 8),
            Text('Fac Médecine (UCAD) Dakar'),
          ],
        ),
        SizedBox(height: 16),
        Text('A propos', style: TextStyle(fontWeight: FontWeight.bold)),
        SizedBox(height: 8),
        Text(
          'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
        ),
      ],
    );
  }
}
