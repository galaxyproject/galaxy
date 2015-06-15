import sys
import argparse
import pandas as pd
import numexpr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
matplotlib.style.use('ggplot')

def mutsig_viz(sig_genes, output, n_genes, q_val):
	with PdfPages(output) as pdf:

		# prepare data
		d = pd.read_csv(sig_genes, sep = '\t')
		d['total'] = d['n_nonsilent'] + d['n_silent'] + d['n_noncoding']
		# sort and remove genes with < 0.1 FDR
		q = 'q<='+str(q_val)
		fd = d.sort('q').query(q)

		# plot silent / nonsilent mutations / noncoding mutations
		if n_genes is None or int(n_genes) > 125:
			if len(d) < 125:
				n_genes = len(d)
			else:
				n_genes = 125
		sm = fd.sort('total', ascending = False)[:int(n_genes)]
		
		nsm = sm.sort('total', ascending = True)

		plt.figure()
		ax = nsm.plot(x='gene', y = ['n_nonsilent', 'n_silent', 'n_noncoding'], kind='barh', stacked=True)
		ax.set_xlabel('Mutation Count', fontsize=8)
		ax.set_ylabel('Gene', fontsize=8)
		ax.set_title('Top '+ str(n_genes) +' Significant Genes ('+q+')', fontsize=4)

		l = plt.legend(loc="best")
		l.get_texts()[0].set_text('Nonsilent')

		l.get_texts()[1].set_text('Silent')
		l.get_texts()[2].set_text('Noncoding')

		if len(nsm) >= 100:
			ax.tick_params(axis='y', labelsize=3)
		elif len(nsm) >= 50 and len(nsm) < 100:
			ax.tick_params(axis='y', labelsize=5)
		else:
			ax.tick_params(axis='y', labelsize=7)

		pdf.savefig()
		plt.close()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Mutsig Significant Genes File.')
	parser.add_argument('-i', '--input', dest = "sig_genes", nargs='?', default=None, help='Input file.')
	parser.add_argument('-o', '--output', dest = "output", nargs='?', default=None, help='Output file.')
	parser.add_argument('-n', '--n_genes', dest = "n_genes", nargs='?', default=None, help='Number of genes to plot.')
	parser.add_argument('-q', '--q_val', dest = "q_val", nargs='?', default=0.1, help='Q-value cut off.')
	args = parser.parse_args()

	mutsig_viz(vars(args)['sig_genes'], vars(args)['output'], vars(args)['n_genes'], vars(args)['q_val'])