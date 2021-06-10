"""
This module implements the `se find-mismatched-dashes` command.
"""

import argparse

import regex
from rich import box
from rich.console import Console
from rich.table import Table

import se
import se.easy_xml


def find_mismatched_dashes(plain_output: bool) -> int:
	"""
	Entry point for `se find-mismatched-dashes`
	"""

	parser = argparse.ArgumentParser(description="Find words with mismatched dashes in a set of XHTML files. For example, `extra-physical` in one file and `extraphysical` in another.")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME) # Syntax highlighting will do weird things when printing paths
	return_code = 0
	dashed_words = {}
	mismatches = {}
	target_filenames = se.get_target_filenames(args.targets, ".xhtml")
	files_xhtml = []

	# Read files and cache for later
	for filename in target_filenames:
		try:
			with open(filename, "r", encoding="utf-8") as file:
				# Remove all attributes
				dom = se.easy_xml.EasyXmlTree(file.read())
				for node in dom.xpath("//*[@*]"):
					for key, _ in node.attrs.items():
						node.remove_attr(key)

				files_xhtml.append(dom.to_string())

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code

	# Create a list of dashed words
	for xhtml in files_xhtml:
		for word in regex.findall(r"\b\w+\-\w+\b", xhtml):
			lower_word = word.lower()

			if lower_word in dashed_words:
				dashed_words[lower_word] = dashed_words[lower_word] + 1
			else:
				dashed_words[lower_word] = 1

	# Now iterate over the list and search files for undashed versions of the words
	if dashed_words:
		for xhtml in files_xhtml:
			for dashed_word, count in dashed_words.items():
				plain_word = dashed_word.replace("-", "")

				matches = regex.findall(fr"\b{plain_word}\b", xhtml, flags=regex.IGNORECASE)

				if matches:
					if dashed_word in mismatches:
						if plain_word in mismatches[dashed_word]:
							mismatches[dashed_word][plain_word] = (count, mismatches[dashed_word][plain_word][1] + len(matches))
						else:
							mismatches[dashed_word][plain_word] = (count, len(matches))

					else:
						mismatches[dashed_word] = {}
						mismatches[dashed_word][plain_word] = (count, len(matches))

	lines = []

	for dashed_word, child in mismatches.items():
		for plain_word, counts in child.items():
			lines.append((dashed_word, counts[0], plain_word, counts[1]))

	lines.sort()

	if lines:
		if plain_output:
			for dashed_word, dashed_word_count, plain_word, plain_word_count in lines:
				console.print(f"{dashed_word} ({dashed_word_count})\t{plain_word} ({plain_word_count})")

		else:
			table = Table(show_header=False, show_lines=True, box=box.HORIZONTALS)
			table.add_column("Dashed word")
			table.add_column("Count", style="dim", no_wrap=True)
			table.add_column("Plain word")
			table.add_column("Count", style="dim", no_wrap=True)

			for dashed_word, dashed_word_count, plain_word, plain_word_count in lines:
				table.add_row(dashed_word, f"({dashed_word_count})", plain_word, f"({plain_word_count})")

			console.print(table)

	return return_code
