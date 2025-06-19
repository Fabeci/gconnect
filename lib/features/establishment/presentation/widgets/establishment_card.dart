import 'package:flutter/material.dart';
import 'package:gconnect/features/establishment/domain/entities/establishment.dart';
import 'package:gconnect/features/establishment/presentation/pages/join_establishment_page.dart';
import 'package:go_router/go_router.dart';

class EtablissementCard extends StatelessWidget {
  final Establishment etablissement;

  const EtablissementCard({super.key, required this.etablissement});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(vertical: 5),
      margin: EdgeInsets.symmetric(vertical: 5),
      child: ListTile(
        onTap: () {
          context.pushNamed(
            'establishment-detail',
            extra: etablissement,
          );
        },
        leading: CircleAvatar(
          backgroundImage: AssetImage(etablissement.logoUrl),
          radius: 24,
        ),
        title: Text(etablissement.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(etablissement.description, maxLines: 2, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 6),
            Row(
              children: [
                ...etablissement.relationAvatars.map((avatar) => Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: CircleAvatar(radius: 10, backgroundImage: AssetImage(avatar)),
                )),
                const SizedBox(width: 6),
                Text('+${etablissement.memberCount} membres', style: const TextStyle(fontSize: 12)),
              ],
            ),
          ],
        ),
        trailing: ElevatedButton(
          onPressed: () {
            showJoinEstablishmentModal(context);
          },
          style: ElevatedButton.styleFrom(
            shape: StadiumBorder(),
            backgroundColor: Colors.grey[200],
            foregroundColor: Colors.blue,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            elevation: 0,
          ),
          child: const Text("Rejoindre"),
        ),
      ),
    );
  }
}
