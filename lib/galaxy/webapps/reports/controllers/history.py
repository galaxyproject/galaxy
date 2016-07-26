import galaxy.model
import collections
import logging
import sqlalchemy as sa

from galaxy import util
from galaxy.web.base.controller import BaseUIController, web

from markupsafe import escape
from sqlalchemy import and_

log = logging.getLogger( __name__ )


def int_to_octet(size):
    try:
        size = float(size)
    except ValueError:
        return "???"
    except TypeError:
        if size is None:
            return "0 o"
        return "???"
    units = ("o", "Ko", "Mo", "Go", "To")
    no_unit = 0
    while (size >= 1000):
        size /= 1000.
        no_unit += 1
    try:
        return "%.2f %s" % (size, units[no_unit])
    except IndexError:
        return "%.0f %s" % (size * ((no_unit - len(units) + 1) * 1000.), units[-1] )


class History( BaseUIController ):
    """
    Class defining functions used by reports to make requests to get
    informations and fill templates before being displayed.
    The name of function must be the same as as the field "action" of
    the "href" dict, in .mako templates (templates/webapps/reports).
    """
    @web.expose
    def history_and_dataset_per_user( self, trans, **kwd ):
        """
        fill history_and_dataset_per_user.mako template with:
            - user email
            - the number of history and their size
            - the number of dataset
        """
        message = escape( util.restore_text( kwd.get( 'message', '' ) ) )
        user_cutoff = int( kwd.get( 'user_cutoff', 60 ) )

        # sort by history space, or by user mail or by number of history/dataset
        sort_by = kwd.get( 'sorting', 'User' )
        sorting = 0 if sort_by == 'User' else 1 if sort_by == "HSort" else 2 if sort_by == "DSort" else 3
        descending = 1 if kwd.get( 'descending', 'desc' ) == 'desc' else -1

        # select count (h.id) as history, u.email as email
        # from history h, galaxy_user u
        # where h.user_id = u.id and h.deleted='f'
        # group by email order by email desc
        histories = sa.select(
            (sa.func.count( galaxy.model.History.table.c.id ).label( 'history' ),
             galaxy.model.User.table.c.email.label( 'email' )),
            from_obj=[sa.outerjoin(galaxy.model.History.table, galaxy.model.User.table)],
            whereclause=and_(galaxy.model.History.table.c.user_id == galaxy.model.User.table.c.id,
                             galaxy.model.History.table.c.deleted == 'f'),
            group_by=['email'],
            order_by=[ sa.desc( 'email' ), 'history' ] )

        # select u.email, count(d.id)
        # from galaxy_user u, dataset d, history_dataset_association hd,history h
        # where d.id=hd.dataset_id and h.id=hd.history_id and u.id = h.user_id and h.deleted='f'
        # group by u.email;
        datasets = sa.select(
            (sa.func.count( galaxy.model.Dataset.table.c.id ).label( 'dataset' ),
             sa.func.sum( galaxy.model.Dataset.table.c.total_size ).label( 'size' ),
             galaxy.model.User.table.c.email.label( 'email' ) ),
            from_obj=[ galaxy.model.User.table,
                       galaxy.model.Dataset.table,
                       galaxy.model.HistoryDatasetAssociation.table,
                       galaxy.model.History.table],
            whereclause=and_(galaxy.model.Dataset.table.c.id == galaxy.model.HistoryDatasetAssociation.table.c.dataset_id,
                             galaxy.model.History.table.c.id == galaxy.model.HistoryDatasetAssociation.table.c.history_id,
                             galaxy.model.History.table.c.user_id == galaxy.model.User.table.c.id,
                             galaxy.model.History.table.c.deleted == 'f'),
            group_by=[ 'email' ] )

        # execute requests, replace None fields by "Unknown"
        # transform lists to dict with email as key and
        # number of (history/dataset)/size of history as value
        histories = dict( [ ( _.email if _.email is not None else "Unknown", int( _.history ) )
                            for _ in histories.execute() ] )
        datasets = dict( [ ( _.email if _.email is not None else "Unknown", (int( _.dataset ), int( _.size )) )
                           for _ in datasets.execute() ] )

        sorting_functions = [
            lambda first, second: descending if first[0].lower() > second[0].lower() else -descending,
            lambda first, second: descending if histories.get(first, 0) < histories.get(second, 0) else -descending,
            lambda first, second: descending if datasets.get(first, [0])[0] < datasets.get(second, [0])[0] else -descending,
            lambda first, second: descending if datasets.get(first, [0, 0])[1] < datasets.get(second, [0, 0])[1] else -descending
        ]

        # fetch all users
        users = list(set(histories.keys()) | set(datasets.keys()))

        # sort users depending on sort function, defined by user choices
        users.sort(sorting_functions[sorting])
        if user_cutoff > 0:
            users = users[:user_cutoff]

        # to keep ordered
        data = collections.OrderedDict()
        for user in users:
            dataset = datasets.get(user, [0, 0])
            history = histories.get(user, 0)
            data[user] = ("%d (%s)" % ( history, int_to_octet( dataset[1] ) ), dataset[0] )

        return trans.fill_template( '/webapps/reports/history_and_dataset_per_user.mako',
                                    data=data,
                                    user_cutoff=user_cutoff,
                                    sorting=sorting,
                                    descending=descending,
                                    message=message )

    @web.expose
    def history_and_dataset_type( self, trans, **kwd ):
        """
        fill history_and_dataset_type.mako template with:
            - the name of history
            - the number of dataset foreach type
        """
        message = escape( util.restore_text( kwd.get( 'message', '' ) ) )
        user_cutoff = int( kwd.get( 'user_cutoff', 60 ) )
        descending = 1 if kwd.get( 'descending', 'desc' ) == 'desc' else -1
        user_selection = kwd.get( 'user_selection', None)

        # select d.state, h.name
        # from dataset d, history h , history_dataset_association hda
        # where hda.history_id=h.id and hda.dataset_id=d.id order by h.state;
        from_obj = [ galaxy.model.Dataset.table, galaxy.model.History.table, galaxy.model.HistoryDatasetAssociation.table]
        if user_selection is not None:
            from_obj.append( galaxy.model.User.table )
            whereclause = and_( galaxy.model.Dataset.table.c.id == galaxy.model.HistoryDatasetAssociation.table.c.dataset_id,
                                galaxy.model.History.table.c.id == galaxy.model.HistoryDatasetAssociation.table.c.history_id,
                                galaxy.model.User.table.c.id == galaxy.model.History.table.c.user_id,
                                galaxy.model.User.table.c.email == user_selection )
        else:
            whereclause = and_(galaxy.model.Dataset.table.c.id == galaxy.model.HistoryDatasetAssociation.table.c.dataset_id,
                               galaxy.model.History.table.c.id == galaxy.model.HistoryDatasetAssociation.table.c.history_id)
        histories = sa.select( ( galaxy.model.Dataset.table.c.state.label( 'state' ),
                                 galaxy.model.History.table.c.name.label( 'name' ) ),
                               from_obj=from_obj,
                               whereclause=whereclause,
                               order_by=[ 'name' ] )

        # execute requests, replace None fields by "Unknown"
        data = [ ( _.name if _.name is not None else "NoNamedHistory", _.state )
                 for _ in histories.execute() ]

        # sort by names descending or ascending
        data.sort(lambda first, second: descending if first[0].lower() > second[0].lower() else -descending)

        # fetch names in the first list and status in the second
        if data:
            names, status = zip( *tuple(data) )
        else:
            names, status = [], []

        possible_status = {"ok": 0, "upload": 1, "paused": 2, "queued": 3, "error": 4, "discarded": 5}
        number_of_possible_status = len( possible_status ) + 1  # + 1 to handle unknown status!

        # to keep ordered
        datas = collections.OrderedDict()
        for no, name in enumerate(names):
            if name not in datas:
                if user_cutoff > 0:
                    if len( datas ) == user_cutoff:
                        break
                # creation of a list containing the number of each status
                datas[name] = ['-'] * number_of_possible_status
            # to not execute it several times, we put it in a variable...
            no_status = possible_status.get(status[no], 6)
            if datas[name][no_status] == '-':
                datas[name][no_status] = 0
            datas[name][no_status] += 1

        return trans.fill_template( '/webapps/reports/history_and_dataset_type.mako',
                                    data=datas,
                                    user_cutoff=user_cutoff,
                                    descending=descending,
                                    message=message )
