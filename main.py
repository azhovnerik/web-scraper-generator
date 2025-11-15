#!/usr/bin/env python3
"""Головний скрипт для генерації скрейперів"""

import argparse
from generator import ScraperGenerator


TEST_SITES = [
    "https://anadea.info/",
    "https://www.thefamilylawco.co.uk/",
    "https://www.ceb.com/",
    "https://info.wealthcounsel.com/",
    "https://circlesup.com/",
    "https://divorceseparationcoach.co.uk/",
    "https://www.journalofaccountancy.com/",
    "https://www.biggerpockets.com/",
    "https://www.realself.com/",
    "https://nutrition.org/",
    "https://acupuncturetoday.com/",
]


def main():
    parser = argparse.ArgumentParser(
        description="Generate web scrapers for article-based websites"
    )

    parser.add_argument('--url', type=str, help='Single URL to generate scraper for')
    parser.add_argument('--batch', action='store_true', help='Generate scrapers for all test sites')
    parser.add_argument('--test-sites', action='store_true', help='Show list of test sites')
    parser.add_argument('--output', type=str, default='scrapers', help='Output directory')
    parser.add_argument('--max-retries', type=int, default=2, help='Maximum retries')
    parser.add_argument(
        '--local',
        action='store_true',
        help='Process local HTML directories instead of URLs'
    )

    args = parser.parse_args()

    if args.test_sites:
        print("\nTest sites from the assignment:")
        print("=" * 60)
        for i, site in enumerate(TEST_SITES, 1):
            print(f"{i:2}. {site}")
        print("=" * 60)
        return

    generator = ScraperGenerator(output_dir=args.output)

    if args.url:
      if args.local:
         print(f"\nGenerating scraper for LOCAL directory: {args.url}")
      else:
         print(f"\nGenerating scraper for: {args.url}")

      result = generator.generate(args.url, max_retries=args.max_retries, is_local=args.local)

      if result['success']:
         print(f"\n✓ Success! Scraper saved to: {result['filepath']}")
         print(f"  Validation score: {result['validation_score']:.2%}")
      else:
        print(f"\n✗ Failed: {result.get('error', 'Unknown error')}")

      return

    if args.batch:
        print("\nGenerating scrapers for all test sites...")
        print("=" * 60)

        results = generator.generate_batch(TEST_SITES)

        successful = sum(1 for r in results.values() if r.get('success', False))
        total = len(TEST_SITES)

        print(f"\n{'=' * 60}")
        print(f"BATCH GENERATION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total sites: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success rate: {successful/total:.1%}")
        print(f"{'=' * 60}\n")

        print("Detailed results:")
        for url, result in results.items():
            if result.get('success'):
                score = result.get('validation_score', 0)
                print(f"  ✓ {url} (score: {score:.2%})")
            else:
                error = result.get('error', 'Unknown error')
                print(f"  ✗ {url} - {error}")
        return

    parser.print_help()
    print("\nExamples:")
    print("  python main.py --url https://anadea.info/")
    print("  python main.py --batch")
    print("  python main.py --test-sites")


if __name__ == "__main__":
    main()
