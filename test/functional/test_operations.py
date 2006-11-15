from base.twilltestcase import TwillTestCase

# the numbering of the tests is essential as they
# will be executed in order, sorted by name
class Operations(TwillTestCase):

    def test_00_first(self): # must be first
        "Uploading data"
        self.clear_history()
        self.upload_file('1.bed', dbkey='hg17')
        self.upload_file('2.bed', dbkey='hg17')
    
    def test_intersect(self):
        "Intersect"
        self.run_tool('Intersect1', input1='1.bed', input2="2.bed", min=1)
        self.check_data('op-intersect.dat')
    
    def test_join(self):
        "Join"
        self.run_tool('Join1', input1='1.bed', input2="2.bed", min=1)
        self.check_data('op-join.dat')
    
    def test_merge(self):
        "Merge"
        self.run_tool('Merge1', input='1.bed')
        self.check_data('op-merge.dat')
    
    def test_overlap(self):
        "Overlap"
        self.run_tool('Overlap1', input1='1.bed', input2="2.bed", min=1)
        self.check_data('op-overlap.dat')
    
    def test_proximity(self):
        "Proximity"
        self.run_tool('Proximity1', input1='1.bed', input2="2.bed", within="-within", up=0, down=0)
        self.check_data('op-proximity.dat')

    def test_subtract(self):
        "Subtract"
        self.run_tool('Subtract1', input1='1.bed', input2="2.bed")
        self.check_data('op-subtract.dat')

    def test_union(self):
        "Union"
        self.run_tool('Union2', input1='1.bed', input2="2.bed")
        self.check_data('op-union.dat')

    def test_cluster(self):
        "Cluster"
        self.run_tool('Cluster1', input='1.bed', num=2, size=10)
        self.check_data('op-cluster.dat')

    def test_clustermerge(self):
        "Cluster merge"
        self.run_tool('ClusterMerge1', input='1.bed', num=2, size=10)
        self.check_data( 'op-clustermerge.dat')

    def test_complement(self):
        "Complement"
        self.run_tool('Complement1', input='1.bed')
        self.check_data('op-complement.dat')

    def test_interval_complement(self):
        "Interval Complement"
        self.run_tool('interval_complement1', input='1.bed')
        self.check_data('op-interval-complement.dat')

    def test_covdens(self):
        "covDensity"
        self.run_tool('covDensity1', input1='1.bed', input2="2.bed")
        self.check_data('op-covdensity.dat')

    def test_interval_covdens(self):
        "Interval covDensity"
        self.run_tool('interval_coverage', input1='1.bed')
        self.check_data('op-interval-covdensity.dat')

    def test_difference(self):
        "Difference"
        self.run_tool('Difference1', input1='1.bed', input2="2.bed")
        self.check_data('op-difference.dat')

    def test_extend(self):
        "Extend"
        self.run_tool('Extend1', input='1.bed', len=100, where="ud")
        self.check_data('op-extend.dat')

    def test_zz_fill_the_queue(self): # must be last (when sorted on the name)
        "Stress test, running all operations"
        
        self.test_00_first()

        self.run_tool('Intersect1', input1='1.bed', input2="2.bed", min=1)
        self.run_tool('Join1', input1='1.bed', input2="2.bed", min=1)
        self.run_tool('Merge1', input='1.bed')
        self.run_tool('Overlap1', input1='1.bed', input2="2.bed", min=1)
        
        self.run_tool('Proximity1', input1='1.bed', input2="2.bed", within="-within", up=0, down=0)
        self.run_tool('Subtract1', input1='1.bed', input2="2.bed")
        self.run_tool('Union2', input1='1.bed', input2="2.bed")
        self.run_tool('Cluster1', input='1.bed', num=2, size=10)
       
        self.run_tool('ClusterMerge1', input='1.bed', num=2, size=10)
        self.run_tool('Complement1', input='1.bed')
        self.run_tool('covDensity1', input1='1.bed', input2="2.bed")
        self.run_tool('Difference1', input1='1.bed', input2="2.bed")
        self.run_tool('interval_complement1', input='1.bed')
        self.run_tool('interval_coverage', input1='1.bed')
        self.run_tool('Extend1', input='1.bed', len=100, where="ud")
        
        self.wait()
        names = [ 
            'op-intersect.dat','op-join.dat', 'op-merge.dat', 'op-overlap.dat',
            'op-proximity.dat', 'op-subtract.dat', 'op-union.dat', 'op-cluster.dat',
            'op-clustermerge.dat', 'op-complement.dat', 'op-covdensity.dat', 'op-difference.dat',
	    'op-interval-complement.dat', 'op-interval-covdensity.dat', 'op-extend.dat'
        ]
        for idx, name in enumerate(names):
            self.check_data(name, hid=idx+3, wait=False)

