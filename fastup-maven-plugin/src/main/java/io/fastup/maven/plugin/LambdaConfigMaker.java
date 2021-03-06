/*
 * Tvarit is an AWS DevOps Automation Tool for JEE applications.
 * See http://www.tvarit.io
 *     Copyright (C) 2016. Sachin Dole.
 *
 *     This program is free software: you can redistribute it and/or modify
 *     it under the terms of the GNU General Public License as published by
 *     the Free Software Foundation, either version 3 of the License, or
 *     (at your option) any later version.
 *
 *     This program is distributed in the hope that it will be useful,
 *     but WITHOUT ANY WARRANTY; without even the implied warranty of
 *     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *     GNU General Public License for more details.
 *
 *     You should have received a copy of the GNU General Public License
 *     along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

package io.fastup.maven.plugin;

import com.amazonaws.util.json.JSONException;
import com.amazonaws.util.json.JSONWriter;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

class LambdaConfigMaker {
    public static void main(String[] args) throws IOException {
        final File configFile = new File(args[3] + "\\src\\main\\lambda\\plugin_config.py");
        try {
            final FileWriter lambdaConfigFile = new FileWriter(configFile);
            lambdaConfigFile.write("plugin_config = ");
            new JSONWriter(lambdaConfigFile).object().
                    key("groupId").value(args[0]).
                    key("artifactId").value(args[1]).
                    key("version").value(args[2]).
                    endObject();
            lambdaConfigFile.flush();
            lambdaConfigFile.close();
        } catch (JSONException e) {
            throw new RuntimeException(e);
        }
    }
}
