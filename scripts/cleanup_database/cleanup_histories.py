from history_table_pruner import HistoryTablePruner

if __name__ == "__main__":
    # TODO setup args: batch_size, max_create_time, db_url
    db_url = "get this from config"  # TODO
    htp = HistoryTablePruner(db_url)
    htp.run()
