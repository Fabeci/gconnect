import 'package:flutter/material.dart';
import 'package:gconnect/features/establishment/domain/entities/establishment.dart';
import 'package:gconnect/features/establishment/presentation/pages/join_establishment_page.dart';

class EstablishmentDetailPage extends StatelessWidget {
  final Establishment establishment;

  const EstablishmentDetailPage({super.key, required this.establishment});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        backgroundColor: const Color(0xFFF8F8F8),
        body: Column(
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                SizedBox(
                  height: 180,
                  width: double.infinity,
                  child: Image.network(
                    establishment.banner,
                    fit: BoxFit.cover,
                    loadingBuilder: (context, child, loadingProgress) {
                      if (loadingProgress == null) return child;
                      return const Center(child: CircularProgressIndicator());
                    },
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        color: Colors.grey[200],
                        child: const Center(child: Icon(Icons.broken_image, size: 40)),
                      );
                    },
                  ),
                ),
                // Bouton de retour
                Positioned(
                  top: 40,
                  left: 16,
                  child: CircleAvatar(
                    backgroundColor: Colors.black.withOpacity(0.4),
                    child: IconButton(
                      icon: const Icon(Icons.arrow_back, color: Colors.white),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                ),
                // Logo en bas
                Positioned(
                  bottom: -40,
                  left: 0,
                  right: 0,
                  child: CircleAvatar(
                    radius: 40,
                    backgroundColor: Colors.white,
                    child: CircleAvatar(
                      radius: 37,
                      backgroundImage: AssetImage(establishment.logoUrl),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 48),
            Text(
              establishment.name,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              child: Text(
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.black87),
              ),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                        onPressed: () {
                          showJoinEstablishmentModal(context);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue, // ou une couleur plus vive selon ta charte
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(24),
                          ),
                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                          elevation: 4,
                          shadowColor: Colors.black.withOpacity(0.2),
                        ),
                        child: const Text('Rejoindre', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton(
                        onPressed: () {},
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.blue,
                          side: const BorderSide(color: Colors.blue),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(24),
                          ),
                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                        ),
                        child: const Text('Message', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const TabBar(
              indicatorColor: Colors.blue,
              labelColor: Colors.blue,
              unselectedLabelColor: Colors.black54,
              tabs: [
                Tab(icon: Icon(Icons.info_outline), text: 'Infos'),
                Tab(icon: Icon(Icons.bar_chart), text: 'Activités'),
                Tab(icon: Icon(Icons.group_outlined), text: 'Membres'),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: TabBarView(
                children: [
                  Center(child: Text("Infos")),
                  Center(child: Text("Activités")),
                  Center(child: Text("Membres")),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
