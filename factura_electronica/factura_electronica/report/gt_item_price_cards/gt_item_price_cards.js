// Copyright (c) 2026, Si Hay Sistema and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GT Item Price Cards"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
    },
    {
      fieldname: "price_list",
      label: __("Price List"),
      fieldtype: "Link",
      options: "Price List",
      default: frappe.defaults.get_default("selling_price_list"),
      reqd: 1,
      get_query: function () {
        return {
          filters: { enabled: 1 },
        };
      },
    },
    {
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      options: "Item Group",
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "search",
      label: __("Search"),
      fieldtype: "Data",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    if (column && column.fieldname === "change_percent") {
      return gt_item_price_cards_percent_html(value);
    }
    return default_formatter(value, row, column, data);
  },

  onload: function (report) {
    gt_item_price_cards_install_style();
    gt_item_price_cards_wrap_refresh(report);
    gt_item_price_cards_add_toggle(report);
  },

  after_datatable_render: function () {
    gt_item_price_cards_render(frappe.query_report);
  },
};

function gt_item_price_cards_wrap_refresh(report) {
  if (!report || !report.refresh || report.refresh._gt_item_price_cards) {
    return;
  }
  var inner_refresh = report.refresh.bind(report);
  var wrapped = function () {
    gt_item_price_cards_remove(report);
    return inner_refresh.apply(report, arguments);
  };
  wrapped._gt_item_price_cards = 1;
  report.refresh = wrapped;
}

function gt_item_price_cards_add_toggle(report) {
  if (!report.page || !report.page.add_inner_button) {
    return;
  }
  if (report.page.inner_toolbar) {
    report.page.inner_toolbar.find(".gt-price-cards-toggle").remove();
  }
  var button = report.page.add_inner_button("Ver tabla", function () {
    report._gt_price_mode = report._gt_price_mode === "table" ? "cards" : "table";
    var label = report._gt_price_mode === "table" ? "Ver tarjetas" : "Ver tabla";
    if (button && button.text) {
      button.text(label);
    }
    gt_item_price_cards_apply_mode(report);
  });
  if (button && button.addClass) {
    button.addClass("gt-price-cards-toggle");
  }
}

function gt_item_price_cards_remove(report) {
  if (report && report.$report) {
    report.$report.find(".gt-price-cards").remove();
    report.$report.removeClass("gt-price-cards-active");
  }
}

function gt_item_price_cards_render(report) {
  if (!report || !report.$report) {
    return;
  }
  report.$report.find(".gt-price-cards").remove();
  var rows = report.data || [];
  if (!rows.length) {
    gt_item_price_cards_apply_mode(report);
    return;
  }
  var wrap = document.createElement("div");
  wrap.className = "gt-price-cards";
  rows.forEach(function (row) {
    if (!row || !row.item_code) {
      return;
    }
    wrap.appendChild(gt_item_price_cards_card(row));
  });
  report.$report.prepend(wrap);
  gt_item_price_cards_apply_mode(report);
}

function gt_item_price_cards_apply_mode(report) {
  if (!report || !report.$report) {
    return;
  }
  var show_cards = report._gt_price_mode !== "table";
  report.$report.toggleClass("gt-price-cards-active", show_cards);
}

function gt_item_price_cards_card(row) {
  var card = gt_item_price_cards_el("article", "gt-price-card");
  card.appendChild(gt_item_price_cards_media(row));

  var body = gt_item_price_cards_el("div", "gt-price-card__body");
  body.appendChild(gt_item_price_cards_el("div", "gt-price-card__name", row.item_name || row.item_code));

  var code_bits = [row.item_code];
  if (row.uom) {
    code_bits.push(row.uom);
  }
  if (row.item_group) {
    code_bits.push(row.item_group);
  }
  body.appendChild(gt_item_price_cards_el("div", "gt-price-card__code", code_bits.join(" · ")));
  body.appendChild(
    gt_item_price_cards_el(
      "div",
      "gt-price-card__price",
      gt_item_price_cards_money(row.current_price, row.currency)
    )
  );
  body.appendChild(gt_item_price_cards_change(row));
  var previous = gt_item_price_cards_el("div", "gt-price-card__meta");
  if (row.previous_price === null || row.previous_price === undefined || row.previous_price === "") {
    previous.textContent = "Sin precio anterior";
  } else {
    previous.textContent = "Anterior: " + gt_item_price_cards_money(row.previous_price, row.currency);
  }
  body.appendChild(previous);
  var when = gt_item_price_cards_el("div", "gt-price-card__meta");
  when.textContent = "Último cambio: " + gt_item_price_cards_date(row.change_date);
  body.appendChild(when);
  card.appendChild(body);
  return card;
}

function gt_item_price_cards_media(row) {
  var media = gt_item_price_cards_el("div", "gt-price-card__media");
  var initials = gt_item_price_cards_initials(row.item_name || row.item_code);
  if (!row.image) {
    media.textContent = initials;
    return media;
  }
  var image = document.createElement("img");
  image.alt = "";
  image.src = row.image;
  image.addEventListener("error", function () {
    if (image.parentNode) {
      image.parentNode.removeChild(image);
    }
    media.textContent = initials;
  });
  media.appendChild(image);
  return media;
}

function gt_item_price_cards_change(row) {
  var node = gt_item_price_cards_el("div", "gt-price-card__change");
  var html = gt_item_price_cards_percent_html(row.change_percent);
  if (!html) {
    node.textContent = "Sin cambio de precio";
    return node;
  }
  node.innerHTML = html;
  return node;
}

function gt_item_price_cards_percent_html(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  var number = Number(value);
  if (isNaN(number)) {
    return "";
  }
  var arrow = "";
  var css = "gt-price-card__flat";
  if (number > 0) {
    arrow = "▲ ";
    css = "gt-price-card__up";
  } else if (number < 0) {
    arrow = "▼ ";
    css = "gt-price-card__down";
  }
  return "<span class='" + css + "'>" + arrow + Math.abs(number).toFixed(2) + "%</span>";
}

function gt_item_price_cards_money(value, currency) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof format_currency === "function") {
    return format_currency(value, currency);
  }
  var number = Number(value);
  if (isNaN(number)) {
    return "";
  }
  return (currency ? currency + " " : "") + number.toFixed(2);
}

function gt_item_price_cards_date(value) {
  if (!value) {
    return "—";
  }
  if (frappe.datetime && frappe.datetime.str_to_user) {
    return frappe.datetime.str_to_user(value);
  }
  return value;
}

function gt_item_price_cards_initials(name) {
  var parts = String(name || "").trim().split(/\s+/);
  var letters = [];
  parts.forEach(function (part) {
    if (part && letters.length < 2) {
      letters.push(part.charAt(0).toUpperCase());
    }
  });
  return letters.join("") || "•";
}

function gt_item_price_cards_el(tag, className, text) {
  var node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined && text !== null) {
    node.textContent = text;
  }
  return node;
}

function gt_item_price_cards_install_style() {
  if (document.getElementById("gt-item-price-cards-style")) {
    return;
  }
  var style = document.createElement("style");
  style.id = "gt-item-price-cards-style";
  style.textContent = [
    ".gt-price-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin:0 0 16px;}",
    ".gt-price-card{display:flex;gap:12px;border:1px solid #e2e6ea;border-radius:8px;background:#fff;padding:12px;min-height:124px;}",
    ".gt-price-card__media{width:72px;height:72px;border-radius:6px;background:#f4f6f8;flex:0 0 72px;display:flex;align-items:center;justify-content:center;overflow:hidden;color:#5a6570;font-weight:600;}",
    ".gt-price-card__media img{width:100%;height:100%;object-fit:cover;}",
    ".gt-price-card__body{min-width:0;}",
    ".gt-price-card__name{font-weight:600;line-height:1.3;}",
    ".gt-price-card__code{color:#6b7280;font-size:12px;margin-top:2px;}",
    ".gt-price-card__price{font-size:18px;font-weight:700;margin-top:6px;}",
    ".gt-price-card__meta{color:#6b7280;font-size:12px;}",
    ".gt-price-card__up{color:green;font-weight:600;}",
    ".gt-price-card__down{color:red;font-weight:600;}",
    ".gt-price-card__flat{color:#374151;font-weight:600;}",
    ".gt-price-cards-active > .datatable{display:none !important;}",
  ].join("");
  document.head.appendChild(style);
}
