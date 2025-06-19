import 'package:flutter/material.dart';
import 'package:gconnect/core/widgets/custom_sccafold_widget.dart';
import 'package:gconnect/features/establishment/domain/entities/establishment.dart';
import 'package:gconnect/features/establishment/presentation/widgets/establishment_card.dart';

class EstablishmentsPage extends StatelessWidget {
  final List<Establishment> etablissements = [
    Establishment(
      name: 'UCAD (Université Cheikh Anta Diop)',
      description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...',
      logoUrl: 'assets/images/establishments/ucad.png',
      banner: 'https://static.vecteezy.com/system/resources/thumbnails/022/530/575/small_2x/school-building-exterior-vector-illustration-png.png',
      memberCount: 45,
      relationAvatars: [
        'assets/images/home/user1.png',
        'assets/images/home/user2.png',
        'assets/images/home/user3.png',
      ],
    ),
    Establishment(
    name: 'UCAO (Université Catholique de l’Afrique de l’Ouest)',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...',
    logoUrl: 'assets/images/establishments/ucao.png',
    banner: 'https://static.vecteezy.com/system/resources/thumbnails/022/530/575/small_2x/school-building-exterior-vector-illustration-png.png',
    memberCount: 109,
    relationAvatars: [
      'assets/images/home/user1.png',
      'assets/images/home/user2.png',
      'assets/images/home/user3.png',
    ],
  ),
  Establishment(
    name: 'ISM (Institut Supérieur de Management)',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...',
    logoUrl: 'assets/images/establishments/ism.png',
    banner: "https://static.vecteezy.com/system/resources/thumbnails/022/530/575/small_2x/school-building-exterior-vector-illustration-png.png",
    memberCount: 67,
    relationAvatars: [
      'assets/images/home/user1.png',
      'assets/images/home/user2.png',
      'assets/images/home/user3.png',
    ],
  ),
  Establishment(
    name: 'ISI (Université Cheikh Anta Diop)',
    description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit...',
    logoUrl: 'assets/images/establishments/isi.png',
    banner: "https://static.vecteezy.com/system/resources/thumbnails/022/530/575/small_2x/school-building-exterior-vector-illustration-png.png",
    memberCount: 89,
    relationAvatars: [
      'assets/images/home/user1.png',
      'assets/images/home/user2.png',
      'assets/images/home/user3.png',
    ],
  ),
    // Ajoute les autres établissements ici
  ];

  EstablishmentsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: CustomScaffold(
        body: Column(
          children: [
            // 🔍 SearchBar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.grey[200],
                borderRadius: BorderRadius.circular(32),
              ),
              child: const TextField(
                decoration: InputDecoration(
                  icon: Icon(Icons.search),
                  border: InputBorder.none,
                  hintText: 'Rechercher...',
                ),
              ),
            ),

            // 🧭 Tabs + filtre
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                children: [
                  const Expanded(
                    child: TabBar(
                      indicatorColor: Colors.blue,
                      labelColor: Colors.blue,
                      unselectedLabelColor: Colors.grey,
                      isScrollable: true,
                      indicatorSize: TabBarIndicatorSize.label,
                      tabs: [
                        Tab(text: "Tout"),
                        Tab(text: "Mes établissements"),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.filter_list),
                    onPressed: () {
                      // Action filtre
                    },
                  )
                ],
              ),
            ),

            // 📋 Liste d'établissements
            Expanded(
              child: TabBarView(
                children: [
                  ListView.separated(
                    itemCount: etablissements.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      return EtablissementCard(etablissement: etablissements[index]);
                    },
                  ),
                  const Center(child: Text("Aucun établissement rejoint.")),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
