import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import 'dart:async';
import 'package:go_router/go_router.dart';

class HomeLoadingPage extends StatefulWidget {
  const HomeLoadingPage({super.key});

  @override
  State<HomeLoadingPage> createState() => _HomeLoadingPageState();
}

class _HomeLoadingPageState extends State<HomeLoadingPage> {
  @override
  void initState() {
    super.initState();

    // Simule un chargement de 2 secondes
    Future.delayed(const Duration(seconds: 2), () {
      context.go('/home');
    });
  }

  Widget _buildCircle({double size = 40}) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: Colors.grey[300],
          shape: BoxShape.circle,
        ),
      );

  Widget _buildRect({double height = 16, double width = double.infinity, double radius = 8}) =>
      Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: Colors.grey[300],
          borderRadius: BorderRadius.circular(radius),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Shimmer.fromColors(
        baseColor: Colors.grey.shade300,
        highlightColor: Colors.grey.shade100,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: ListView(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildCircle(size: 24),
                  _buildCircle(size: 36),
                  Row(
                    children: List.generate(3, (_) => Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: _buildCircle(size: 20),
                    )),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  _buildCircle(size: 40),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildRect(width: 100),
                        const SizedBox(height: 8),
                        _buildRect(width: 150),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              _buildRect(height: 16, width: 300),
              const SizedBox(height: 8),
              _buildRect(height: 16, width: 250),
              const SizedBox(height: 8),
              _buildRect(height: 16, width: 200),
              const SizedBox(height: 20),
              _buildRect(height: 180, radius: 16),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildCircle(size: 20),
                  _buildRect(width: 80, height: 16),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: List.generate(4, (_) => _buildRect(width: 60, height: 14)),
              ),
              const SizedBox(height: 20),
              _buildRect(height: 50, radius: 12),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: List.generate(4, (_) => Column(
                  children: [
                    _buildCircle(size: 50),
                    const SizedBox(height: 8),
                    _buildRect(width: 40, height: 8),
                  ],
                )),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
