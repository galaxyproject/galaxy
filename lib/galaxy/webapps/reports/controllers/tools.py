import logging
from datetime import timedelta

import sqlalchemy as sa
from markupsafe import escape
from sqlalchemy import and_

import galaxy.model
from galaxy.util import (
    restore_text,
    unicodify,
)
from galaxy.webapps.base.controller import (
    BaseUIController,
    web,
)

log = logging.getLogger(__name__)


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
    while size >= 1000:
        size /= 1000.0
        no_unit += 1
    try:
        return f"{size:.2f} {units[no_unit]}"
    except IndexError:
        return f"{size * ((no_unit - len(units) + 1) * 1000.0):.0f} {units[-1]}"


class Tools(BaseUIController):
    """
    Class defining functions used by reports to make requests to get
    informations and fill templates before being displayed.
    The name of function must be the same as as the field "action" of
    the "href" dict, in .mako templates (templates/webapps/reports).
    """

    def formatted(self, date, colored=False):
        splited = str(date).split(",")
        if len(splited) == 2:
            returned = "%s %dH" % (splited[0], int(splited[1].split(":")[0]))
            if colored:
                return f'<font color="red">{returned}</font>'
            return returned
        else:
            splited = tuple(float(_) for _ in str(date).split(":"))
            if splited[0]:
                returned = "%d h. %d min." % splited[:2]
                if colored:
                    return f'<font color="orange">{returned}</font>'
                return returned
            if splited[1]:
                return "%d min. %d sec." % splited[1:3]
            return f"{splited[2]:.1f} sec."

    @web.expose
    def tools_and_job_state(self, trans, **kwd):
        """
        fill tools_and_job_state.mako template with
            - the name of the tool
            - the number of jobs using this tool in state 'ok'
            - the number of jobs using this tool in error
        """

        message = escape(restore_text(kwd.get("message", "")))
        user_cutoff = int(kwd.get("user_cutoff", 60))

        # sort by history space, or by user mail or by number of history/dataset
        sort_by = kwd.get("sorting", "Tool")
        sorting = 0 if sort_by == "Tool" else 1 if sort_by == "ok" else 2
        descending = 1 if kwd.get("descending", "desc") == "desc" else -1
        reverse = descending == 1
        sort_keys = (
            lambda v: v.lower(),
            lambda v: tools_and_jobs_ok.get(v, 0),
            lambda v: tools_and_jobs_error.get(v, 0),
        )

        data = {}

        # select count(id), tool_id from job where state='ok' group by tool_id;
        tools_and_jobs_ok = sa.select(
            (galaxy.model.Job.table.c.tool_id.label("tool"), sa.func.count(galaxy.model.Job.table.c.id).label("job")),
            from_obj=[galaxy.model.Job.table],
            whereclause=(galaxy.model.Job.table.c.state == "ok"),
            group_by=["tool"],
        )

        # select count(id), tool_id from job where state='error' group by tool_id;
        tools_and_jobs_error = sa.select(
            (galaxy.model.Job.table.c.tool_id.label("tool"), sa.func.count(galaxy.model.Job.table.c.id).label("job")),
            from_obj=[galaxy.model.Job.table],
            whereclause=(galaxy.model.Job.table.c.state == "error"),
            group_by=["tool"],
        )

        tools_and_jobs_ok = dict(list(trans.sa_session.execute(tools_and_jobs_ok)))
        tools_and_jobs_error = dict(list(trans.sa_session.execute(tools_and_jobs_error)))

        # select each job name one time
        tools = list(set(tools_and_jobs_ok.keys()) | set(tools_and_jobs_error.keys()))
        tools.sort(key=sort_keys[sorting], reverse=reverse)

        for tool in tools:
            data[tool] = (str(tools_and_jobs_ok.get(tool, "-")), str(tools_and_jobs_error.get(tool, "-")))

        return trans.fill_template(
            "/webapps/reports/tools_and_job_state.mako",
            data=data,
            user_cutoff=user_cutoff,
            sorting=sorting,
            descending=descending,
            message=message,
        )

    @web.expose
    def tools_and_job_state_per_month(self, trans, **kwd):
        """
        fill tools_and_job_state_per_month.mako template with
            - the name of the tool
            - the number of jobs using this tool in state 'ok'
            - the number of jobs using this tool in error
        """

        message = escape(restore_text(kwd.get("message", "")))
        user_cutoff = int(kwd.get("user_cutoff", 60))

        # sort by history space, or by user mail or by number of history/dataset
        # sort_by = kwd.get( 'sorting', 'Tool' )
        # sorting = 0 if sort_by == 'Tool' else 1 if sort_by == 'ok' else 2
        # descending = 1 if kwd.get( 'descending', 'desc' ) == 'desc' else -1
        tool = kwd.get("tool", None)

        if tool is None:
            raise TypeError("Tool can't be None")

        data = {}

        # select count(id), create_time from job where state='ok' and tool_id=$tool group by date;
        date_and_jobs_ok = sa.select(
            (
                sa.func.date(galaxy.model.Job.table.c.create_time).label("date"),
                sa.func.count(galaxy.model.Job.table.c.id).label("job"),
            ),
            from_obj=[galaxy.model.Job.table],
            whereclause=and_(galaxy.model.Job.table.c.state == "ok", galaxy.model.Job.table.c.tool_id == tool),
            group_by=["date"],
        )

        # select count(id), create_time from job where state='error' and tool_id=$tool group by date;
        date_and_jobs_error = sa.select(
            (
                sa.func.date(galaxy.model.Job.table.c.create_time).label("date"),
                sa.func.count(galaxy.model.Job.table.c.id).label("job"),
            ),
            from_obj=[galaxy.model.Job.table],
            whereclause=and_(galaxy.model.Job.table.c.state == "error", galaxy.model.Job.table.c.tool_id == tool),
            group_by=["date"],
        )

        date_and_jobs_ok = dict(list(trans.sa_session.execute(date_and_jobs_ok)))
        date_and_jobs_error = dict(list(trans.sa_session.execute(date_and_jobs_error)))

        # select each date
        dates = list(set(date_and_jobs_ok.keys()) | set(date_and_jobs_error.keys()))
        dates.sort(reverse=True)
        for date in dates:
            date_key = date.strftime("%B %Y")
            if date_key not in data:
                data[date_key] = [int(date_and_jobs_ok.get(date, 0)), int(date_and_jobs_error.get(date, 0))]
            else:
                data[date_key][0] += int(date_and_jobs_ok.get(date, 0))
                data[date_key][1] += int(date_and_jobs_error.get(date, 0))

        return trans.fill_template(
            "/webapps/reports/tools_and_job_state_per_month.mako",
            data=data,
            tool=tool,
            user_cutoff=user_cutoff,
            message=message,
        )

    @web.expose
    def tool_execution_time(self, trans, **kwd):
        """
        Fill the template tool_execution_time.mako with informations:
            - Tool name
            - Tool average execution time
            - last job execution time
            - min and max execution time
        """

        # liste des tools + temps moyen d'exec du job + temps d'execution du dernier job + tps min et max / mois (?)
        user_cutoff = int(kwd.get("user_cutoff", 60))
        sort_by = kwd.get("sort_by", "tool")
        descending = 1 if kwd.get("descending", "desc") == "desc" else -1
        reverse = descending == 1
        sort_by = 0 if sort_by == "tool" else 1 if sort_by == "avg" else 2 if sort_by == "min" else 3
        color = True if kwd.get("color", "") == "True" else False

        data = {}
        ordered_data = {}

        sort_keys = (lambda v: v.lower(), lambda v: data[v]["avg"], lambda v: data[v]["min"], lambda v: data[v]["max"])

        jobs_times = sa.select(
            (
                galaxy.model.Job.table.c.tool_id.label("name"),
                galaxy.model.Job.table.c.create_time.label("create_time"),
                galaxy.model.Job.table.c.update_time.label("update_time"),
                galaxy.model.Job.table.c.update_time - galaxy.model.Job.table.c.create_time,
            ),
            from_obj=[galaxy.model.Job.table],
        )

        jobs_times = [
            (name, (create, update, time)) for name, create, update, time in trans.sa_session.execute(jobs_times)
        ]
        for tool, attr in jobs_times:
            if tool not in data:
                data[tool] = {"last": [(attr[1], attr[0])], "avg": [attr[2]]}
            else:
                data[tool]["last"].append((attr[1], attr[0]))
                data[tool]["avg"].append(attr[2])

        for tool in data:
            data[tool]["min"] = min(data[tool]["avg"])
            data[tool]["max"] = max(data[tool]["avg"])
            last = max(data[tool]["last"])
            data[tool]["last"] = last[0] - last[1]
            data[tool]["avg"] = sum(data[tool]["avg"], timedelta()) / len(data[tool]["avg"])

        tools = list(data.keys())
        if user_cutoff:
            tools = tools[:user_cutoff]
        tools.sort(key=sort_keys[sort_by], reverse=reverse)
        for tool in tools:
            ordered_data[tool] = {
                "min": self.formatted(data[tool]["min"], color),
                "max": self.formatted(data[tool]["max"], color),
                "avg": self.formatted(data[tool]["avg"], color),
                "last": self.formatted(data[tool]["last"], color),
            }

        return trans.fill_template(
            "/webapps/reports/tool_execution_time.mako",
            data=ordered_data,
            descending=descending,
            user_cutoff=user_cutoff,
            sort_by=sort_by,
        )

    @web.expose
    def tool_execution_time_per_month(self, trans, **kwd):
        """
        Fill the template tool_execution_time_per_month.mako with informations:
            - Tool average execution time
            - last job execution time
            - min and max execution time
        """

        # liste des tools + temps moyen d'exec du job + temps d'execution du dernier job + tps min et max / mois(?)
        user_cutoff = int(kwd.get("user_cutoff", 60))
        sort_by = kwd.get("sort_by", "month")
        descending = 1 if kwd.get("descending", "desc") == "desc" else -1
        reverse = descending == 1
        sort_by = 0 if sort_by == "month" else 1 if sort_by == "min" else 2 if sort_by == "max" else 3
        tool = kwd.get("tool", None)
        color = True if kwd.get("color", "") == "True" else False

        if tool is None:
            raise ValueError("Tool can't be None")

        ordered_data = {}
        sort_keys = [(lambda v, i=i: v[i]) for i in range(4)]

        jobs_times = sa.select(
            (
                sa.func.date_trunc("month", galaxy.model.Job.table.c.create_time).label("date"),
                sa.func.max(galaxy.model.Job.table.c.update_time - galaxy.model.Job.table.c.create_time),
                sa.func.avg(galaxy.model.Job.table.c.update_time - galaxy.model.Job.table.c.create_time),
                sa.func.min(galaxy.model.Job.table.c.update_time - galaxy.model.Job.table.c.create_time),
            ),
            from_obj=[galaxy.model.Job.table],
            whereclause=galaxy.model.Job.table.c.tool_id == tool,
            group_by=["date"],
        )

        months = list(trans.sa_session.execute(jobs_times.execute))
        months.sort(key=sort_keys[sort_by], reverse=reverse)
        if user_cutoff:
            months = months[:user_cutoff]

        for month in months:
            ordered_data[str(month[0]).split(" ")[0][:-3]] = (
                self.formatted(month[1], color),
                self.formatted(month[2], color),
                self.formatted(month[3], color),
            )

        return trans.fill_template(
            "/webapps/reports/tool_execution_time_per_month.mako",
            data=ordered_data,
            tool=tool,
            descending=descending,
            user_cutoff=user_cutoff,
            sort_by=sort_by,
        )

    @web.expose
    def tool_error_messages(self, trans, **kwd):
        tool_name = kwd.get("tool", None)
        descending = 1 if kwd.get("descending", "desc") == "desc" else -1
        reverse = descending == 1
        sort_by = 0 if kwd.get("sort_by", "time") == "time" else 1
        cutoff = int(kwd.get("user_cutoff", 60))
        sort_keys = (lambda v: counter[v][1], lambda v: counter[v][0])

        if tool_name is None:
            raise ValueError("Tool can't be none")
        tool_errors = [
            [unicodify(a), b]
            for a, b in trans.sa_session.execute(
                sa.select(
                    (
                        galaxy.model.Job.table.c.tool_stderr,
                        galaxy.model.Job.table.c.create_time,
                    ),
                    from_obj=[galaxy.model.Job.table],
                    whereclause=and_(
                        galaxy.model.Job.table.c.tool_id == tool_name,
                        galaxy.model.Job.table.c.state == "error",
                    ),
                )
            )
        ]

        counter = {}
        for error in tool_errors:
            if error[0] in counter:
                counter[error[0]][0] += 1
            else:
                counter[error[0]] = [1, error[1]]

        data = {}
        keys = list(counter.keys())
        if cutoff:
            keys = keys[:cutoff]
        keys.sort(key=sort_keys[sort_by], reverse=reverse)

        spaces = [" ", "\t", "    "]
        for key in keys:
            new_key = "</br>".join(_ for _ in key.split("\n") if _ and _ not in spaces)
            if len(new_key) >= 100:
                to_replace = []
                words = key.split("\n")
                for word in words:
                    if word in to_replace:
                        continue
                    if words.count(word) > 1:
                        to_replace.append(word)
                for word in to_replace:
                    sentence = f"</br>{word}" * 2
                    count = 2
                    while f"{sentence}</br>{word}" in new_key:
                        sentence += f"</br>{word}"
                        count += 1
                    if sentence in new_key:
                        new_key = new_key.replace(sentence, f"</br>{word}{' [this line in %d times]' % count}")
            data[new_key] = counter[key]

        return trans.fill_template(
            "/webapps/reports/tool_error_messages.mako",
            data=data,
            descending=descending,
            tool_name=tool_name,
            sort_by=sort_by,
            user_cutoff=cutoff,
        )
