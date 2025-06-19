import 'package:flutter/material.dart';
import 'package:gconnect/features/promotions/data/models/promotion_model.dart';
import 'package:gconnect/features/promotions/domain/entities/promotion.dart';
import 'package:gconnect/features/promotions/presentation/widgets/info_tab.dart';
import 'package:gconnect/features/promotions/presentation/widgets/activity_tab.dart';
import 'package:gconnect/features/promotions/presentation/widgets/members_tab.dart';

class PromotionDetailPage extends StatelessWidget {
  final Promotion promotion;

  const PromotionDetailPage({super.key, required this.promotion});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        backgroundColor: Colors.white,
        body: NestedScrollView(
          headerSliverBuilder: (context, innerBoxIsScrolled) => [
            SliverAppBar(
              backgroundColor: Colors.transparent,
              expandedHeight: 200,
              elevation: 0,
              floating: false,
              pinned: true,
              flexibleSpace: FlexibleSpaceBar(
                background: Stack(
                  fit: StackFit.expand,
                  children: [
                    Image.asset(
                      'assets/images/promo/banner.png',
                      fit: BoxFit.cover,
                    ),
                    Container(
                      color: Colors.black.withOpacity(0.3),
                    ),
                    const Positioned(
                      bottom: -20,
                      left: 0,
                      right: 0,
                      child: CircleAvatar(
                        radius: 40,
                        backgroundColor: Colors.white,
                        child: Icon(Icons.school, size: 40),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: Column(
                children: [
                  const SizedBox(height: 40),
                  Text(promotion.title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Chip(label: Text('1ère année 2019')),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 24.0, vertical: 8),
                    child: Text(
                      'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt.',
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ...List.generate(
                        3,
                        (index) => const Padding(
                          padding: EdgeInsets.only(right: 4),
                          child: CircleAvatar(
                            radius: 12,
                            backgroundImage: AssetImage('assets/images/home/user1.png'),
                          ),
                        ),
                      ),
                      Text('${promotion.memberCount} relations'),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      ElevatedButton(
                        onPressed: () {},
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
                        child: const Text('Ajouter', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                      const SizedBox(width: 16),
                      OutlinedButton(
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
                    ],
                  ),

                  const SizedBox(height: 16),
                  const TabBar(
                    labelColor: Colors.black,
                    tabs: [
                      Tab(icon: Icon(Icons.info), text: 'Infos'),
                      Tab(icon: Icon(Icons.bar_chart), text: 'Activités'),
                      Tab(icon: Icon(Icons.group), text: 'Membres'),
                    ],
                  ),
                ],
              ),
            ),
          ],
          body: const TabBarView(
            children: [
              InfoTab(),
              ActivityTab(),
              MembersTab(),
            ],
          ),
        ),
      ),
    );
  }
}
