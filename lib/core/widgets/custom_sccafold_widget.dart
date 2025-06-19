import 'package:flutter/material.dart';
import 'package:gconnect/core/widgets/bottom_navigation_widget.dart';
import 'package:gconnect/core/widgets/drawer_navigation_widget.dart';
import 'package:go_router/go_router.dart';

class CustomScaffold extends StatelessWidget {
  final Widget body;
  final bool showFloatingButton;

  const CustomScaffold({
    super.key,
    required this.body,
    this.showFloatingButton = true
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F8F8),
      appBar: _buildHeader(context),
      drawer: const CustomDrawer(),
      body: body,
      bottomNavigationBar: const BottomNavBar(),
      floatingActionButton: showFloatingButton
          ? Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: Colors.blue,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.2),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: IconButton(
                onPressed: () {},
                icon: Image.asset(
                  'assets/images/posts/edit_post.png',
                  width: 24,
                  height: 24,
                  color: Colors.white,
                ),
              ),
            )
          : null,
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
    );
  }

  PreferredSizeWidget _buildHeader(BuildContext context) {
    return AppBar(
      backgroundColor: Colors.white,
      elevation: 0,
      automaticallyImplyLeading: false,
      title: Row(
        children: [
          Builder(
            builder: (context) => GestureDetector(
              onTap: () => Scaffold.of(context).openDrawer(),
              child: Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.blue, width: 2),
                ),
                child: const CircleAvatar(
                  radius: 18,
                  backgroundImage: AssetImage('assets/images/home/user1.png'),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Center(
              child: Image.asset(
                'assets/images/logo/logo_icon.png',
                height: 64,
              ),
            ),
          ),
          _buildHeaderImageButton(
            'assets/icons/search.png',
            () {
              
            },
            ),
          _buildHeaderImageButton('assets/icons/notification.png',
            () {
              
            },),
          _buildHeaderImageButton('assets/icons/message.png',
            () {
              context.pushNamed(
                'discussions',
              );
            },),
        ],
      ),
    );
  }

  Widget _buildHeaderImageButton(String assetPath, VoidCallback onTap) {
  return Container(
    margin: const EdgeInsets.symmetric(horizontal: 2),
    decoration: const BoxDecoration(
      shape: BoxShape.circle,
      color: Color(0xFFF8F8F8),
    ),
    child: IconButton(
      icon: Image.asset(assetPath, width: 20, height: 20),
      onPressed: onTap,
    ),
  );
}
}
